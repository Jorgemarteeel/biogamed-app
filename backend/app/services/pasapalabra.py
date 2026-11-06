"""One transactional engine for shared Pasapalabra; local transport first."""
from datetime import datetime, timedelta, timezone
from random import SystemRandom

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session, object_session

from app.models import AnswerLog, GameSession, Question, Topic, User
from app.models.pasapalabra import PasapalabraMatch, MatchParticipant, MatchQuestion, MatchCommand
from app.schemas.game_snapshot import StoredQuestion, SharedQuestionSnapshot
from app.services.game_questions import selectable_questions
from app.utils.answers import is_accepted_answer

COUNT = 20
TIME_MS = 600000
RULES = "pasapalabra-local-v1"
RNG = SystemRandom()
UNRESOLVED = {"PENDING", "PASSED"}


def server_now(db):
    value = (db.scalar(select(func.clock_timestamp())) if db.bind.dialect.name == "postgresql"
             else datetime.now(timezone.utc))
    return value.replace(microsecond=(value.microsecond // 1000) * 1000)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def counts(participant):
    correct = sum(q.state == "CORRECT" for q in participant.questions)
    wrong = sum(q.state == "WRONG" for q in participant.questions)
    return {"correct": correct, "wrong": wrong, "pending": COUNT - correct - wrong}


def prepare(db, selection):
    statement = selectable_questions(**selection.model_dump(exclude={"operation_id", "guest_name"}),
                                     mode="PASAPALABRA")
    if db.get(Topic, selection.topic_id) is None:
        raise HTTPException(404, "La temática no existe.")
    available = len(list(db.scalars(statement.with_only_columns(Question.id))))
    return {"available": available, "required": COUNT * 2, "questions_per_player": COUNT,
            "time_per_player_ms": TIME_MS, "can_start": available >= COUNT * 2,
            "selection": selection.model_dump(exclude={"operation_id", "guest_name"})}


def _classification(q):
    from app.services.game import _classification as classify
    return classify(q)


def start_local(db, owner, request):
    return start_shared(db, owner, request)


def start_shared(db, owner, request, *, online_guest=None, auto_commit=True, start_before=None):
    # Serialize starts by this owner, including retries with the same key.
    db.scalar(select(User).where(User.id == owner.id).with_for_update(key_share=True))
    payload = request.model_dump(mode="json", exclude={"operation_id"})
    if online_guest:
        payload.update(play_mode="ONLINE", online_guest_id=str(online_guest.id))
    existing = db.scalar(select(PasapalabraMatch).where(
        PasapalabraMatch.owner_id == owner.id,
        PasapalabraMatch.start_operation_id == str(request.operation_id)))
    if existing:
        if existing.start_payload != payload:
            raise HTTPException(409, {"code": "IDEMPOTENCY_CONFLICT"})
        if auto_commit:
            db.rollback()
        return read_state(db, owner, existing.id) if auto_commit else existing.id
    selection = request.model_dump(exclude={"operation_id", "guest_name"})
    statement = selectable_questions(**selection, mode="PASAPALABRA")
    topic = db.get(Topic, request.topic_id)
    if topic is None:
        raise HTTPException(404, "La temática no existe.")
    # Lock eligible rows until snapshots are made: retirement/editing cannot race the copy.
    candidates = list(db.scalars(statement.order_by(Question.id).with_for_update()))
    if len(candidates) < COUNT * 2:
        raise HTTPException(409, {"code": "INSUFFICIENT_QUESTIONS", "available": len(candidates),
                                  "required": COUNT * 2, "selection": selection})
    chosen = RNG.sample(candidates, COUNT * 2)
    now = server_now(db)
    if start_before is not None and now >= utc(start_before):
        raise HTTPException(409, {"code": "ROOM_EXPIRED"})
    match = PasapalabraMatch(owner_id=owner.id, start_operation_id=str(request.operation_id),
                             start_payload=payload, created_at=now, turn_started_at=now,
                             active_position=RNG.choice([1, 2]), rules_version="pasapalabra-online-v1" if online_guest else RULES,
                             play_mode="ONLINE" if online_guest else "LOCAL")
    db.add(match)
    db.flush()
    for position, name, user_id in [(1, owner.name, owner.id), (2, online_guest.name if online_guest else request.guest_name, online_guest.id if online_guest else None)]:
        assigned = chosen[(position - 1) * COUNT:position * COUNT]
        context = {"topic_name": topic.name,
                   "selection": {"category_id": request.category_id,
                                 "category_name": assigned[0].category.name if request.category_id else None,
                                 "difficulty": request.difficulty,
                                 "difficulty_unknown": request.difficulty_unknown},
                   "questions": [_classification(q) for q in assigned]}
        snapshots = [StoredQuestion.model_validate(q).model_dump() for q in assigned]
        session = None
        if user_id:
            session = GameSession(user_id=user_id, topic_id=topic.id, game_mode="PASAPALABRA",
                                  question_ids=[q.id for q in assigned], content_context=context,
                                  question_snapshot=SharedQuestionSnapshot(version=2, questions=snapshots).model_dump(),
                                  shared_match_id=match.id, format_key=match.rules_version, score=0,
                                  wrong_count=0, pending_count=COUNT, match_status="RUNNING")
            db.add(session)
            db.flush()
        participant = MatchParticipant(match_id=match.id, position=position, name=name,
                                       user_id=user_id, session_id=session.id if session else None)
        db.add(participant)
        db.flush()
        for number, (q, snapshot, classification) in enumerate(zip(assigned, snapshots, context["questions"]), 1):
            db.add(MatchQuestion(match_id=match.id, participant_id=participant.id, number=number,
                                 question_id=q.id, snapshot={**snapshot, "classification": classification}))
    if not auto_commit:
        db.flush()
        return match.id
    db.commit()
    return read_state(db, owner, match.id)


def locked_match(db, owner, match_id):
    db.expire_all()
    match = db.scalar(select(PasapalabraMatch).where(
        PasapalabraMatch.id == match_id,
        ((PasapalabraMatch.owner_id == owner.id) | ((PasapalabraMatch.play_mode == "ONLINE") & PasapalabraMatch.participants.any(MatchParticipant.user_id == owner.id)))).with_for_update())
    if match is None:
        raise HTTPException(404, "La partida no existe.")
    return match


def active(match):
    return next((p for p in match.participants if p.position == match.active_position), None)


def advance(participant, after):
    for offset in range(1, COUNT + 1):
        number = (after - 1 + offset) % COUNT + 1
        if participant.questions[number - 1].state in UNRESOLVED:
            participant.cursor = number
            return True
    participant.status = "FINISHED"
    participant.finish_reason = "RESOLVED"
    return False


def switch_or_finish(match, previous, at):
    other = next(p for p in match.participants if p.position != previous.position)
    candidate = other if other.status == "PLAYING" else previous
    if candidate.status != "PLAYING":
        finish(match, at, "NORMAL")
    else:
        match.active_position = candidate.position
        match.turn_started_at = at


def finish(match, at, outcome, winner=None):
    match.status = "FINISHED"
    match.finished_at = at
    match.outcome = outcome
    match.active_position = None
    match.turn_started_at = None
    if outcome == "NORMAL":
        a, b = (counts(p)["correct"] for p in match.participants)
        winner = 1 if a > b else 2 if b > a else None
    match.winner_position = winner


def settle(match, now):
    """Account for elapsed time, including both deadlines with no intervening requests."""
    while match.status == "RUNNING":
        participant = active(match)
        started = utc(match.turn_started_at)
        elapsed = max(0, (now - started) // timedelta(milliseconds=1))
        spent = min(elapsed, participant.remaining_ms)
        participant.questions[participant.cursor - 1].response_time_ms += spent
        participant.remaining_ms -= spent
        match.turn_started_at = started + timedelta(milliseconds=spent)
        if participant.remaining_ms:
            return
        participant.status = "FINISHED"
        participant.finish_reason = "TIMEOUT"
        match.version += 1
        switch_or_finish(match, participant, match.turn_started_at)


def project(db, match):
    for participant in match.participants:
        if participant.session_id:
            session = db.get(GameSession, participant.session_id)
            tally = counts(participant)
            session.score = tally["correct"]
            session.wrong_count = tally["wrong"]
            session.pending_count = tally["pending"]
            session.match_status = match.status
            session.completion_reason = match.outcome
            session.is_completed = match.status == "FINISHED" and match.outcome == "NORMAL"


def public_state(match, now, viewer_id=None):
    db = object_session(match)
    # Include the command being acknowledged, even with autoflush disabled.
    db.flush()
    resolution_order = {
        (command.result["participant"], command.result["number"]): command.result["version"]
        for command in db.scalars(select(MatchCommand).where(MatchCommand.match_id == match.id))
        if command.result["kind"] == "answer"
    }
    participant = active(match)
    current = participant.questions[participant.cursor - 1] if participant else None
    own = next((p for p in match.participants if p.user_id == viewer_id), match.participants[0] if match.play_mode == "LOCAL" else None)
    if own is None:
        raise HTTPException(404, "La partida no existe.")
    return {"id": match.id, "version": match.version, "play_mode": match.play_mode, "self_position": own.position,
            "rules_version": match.rules_version, "status": match.status, "server_now": now,
            "turn_deadline_at": utc(match.turn_started_at) + timedelta(milliseconds=participant.remaining_ms) if participant else None,
            "active_participant": match.active_position,
            "active_question": {"participant": participant.position, "number": current.number,
                                "text": current.snapshot["text"], "letter": current.snapshot["letter"]} if current and (match.play_mode == "LOCAL" or participant.user_id == viewer_id) else None,
            "participants": [{"position": p.position, "name": p.name, "registered": p.user_id is not None,
                              "status": p.status, "finish_reason": p.finish_reason,
                              "remaining_ms": p.remaining_ms, **counts(p),
                              "slots": [{"number": q.number, "state": q.state} for q in p.questions],
                              "resolved": [{"number": q.number, "text": q.snapshot["text"],
                                            "resolution_order": resolution_order[(p.position, q.number)],
                                            "text_answer": q.text_answer, "exact_word": q.snapshot["exact_word"],
                                            "accepted_answers": q.snapshot["accepted_answers"] or [],
                                            "is_correct": q.state == "CORRECT"}
                                           for q in p.questions if q.state not in UNRESOLVED and (match.play_mode == "LOCAL" or p.user_id == viewer_id)]}
                             for p in match.participants],
            "outcome": match.outcome, "winner_position": match.winner_position,
            "finished_at": match.finished_at,
            "personal_session_id": own.session_id}


def read_state(db, owner, match_id, result_only=False):
    match = locked_match(db, owner, match_id)
    now = server_now(db)
    settle(match, now)
    project(db, match)
    state = public_state(match, now, owner.id)
    db.commit()
    if result_only and state["status"] != "FINISHED":
        raise HTTPException(409, {"code": "MATCH_NOT_FINISHED"})
    return state


def execute(db, owner, match_id, kind, request):
    match = locked_match(db, owner, match_id)
    payload = {"kind": kind, **request.model_dump(mode="json", exclude={"operation_id"})}
    if match.play_mode == "ONLINE":
        payload["actor_id"] = str(owner.id)
    previous = db.scalar(select(MatchCommand).where(MatchCommand.match_id == match.id,
                                                   MatchCommand.operation_id == str(request.operation_id)))
    now = server_now(db)
    settle(match, now)
    project(db, match)
    if previous and previous.payload == payload:
        response = {"operation": previous.result, "state": public_state(match, now, owner.id)}
        db.commit()
        return response
    error = None
    if previous:
        error = "IDEMPOTENCY_CONFLICT"
    elif match.status != "RUNNING":
        error = "MATCH_FINISHED"
    elif request.expected_version != match.version:
        error = "STALE_VERSION"
    participant = next(p for p in match.participants if p.position == request.participant)
    if match.play_mode == "ONLINE" and participant.user_id != owner.id:
        db.commit()
        raise HTTPException(403, {"code": "ONLY_OWN_ACTIONS"})
    if not error and kind != "abandon":
        if participant.position != match.active_position:
            error = "OUT_OF_TURN"
        elif participant.cursor != request.number:
            error = "STALE_QUESTION"
    if error:
        version = match.version
        # Expiration accounting is durable even though this command is rejected.
        db.commit()
        raise HTTPException(409, {"code": error, "version": version})
    question = participant.questions[participant.cursor - 1]
    if kind == "abandon":
        for p in match.participants:
            p.status = "FINISHED"
            p.finish_reason = "ABANDONED" if p.position == participant.position else (p.finish_reason or "OPPONENT_ABANDONED")
        finish(match, now, "ABANDONMENT", 3 - participant.position)
    elif kind == "pass":
        question.state = "PASSED"
        advance(participant, question.number)
        switch_or_finish(match, participant, now)
    else:
        snapshot = question.snapshot
        correct = is_accepted_answer(request.text_answer, snapshot["exact_word"], snapshot["accepted_answers"])
        question.state = "CORRECT" if correct else "WRONG"
        question.text_answer = request.text_answer
        question.answered_at = now
        if participant.session_id:
            db.add(AnswerLog(game_session_id=participant.session_id, question_id=question.question_id,
                             question_text=snapshot["text"], question_type="PASAPALABRA", letter=snapshot["letter"],
                             text_answer=request.text_answer, exact_word=snapshot["exact_word"],
                             accepted_answers=snapshot["accepted_answers"] or [], is_correct=correct,
                             response_time_ms=question.response_time_ms, answered_at=now))
        can_continue = advance(participant, question.number)
        if not correct or not can_continue:
            switch_or_finish(match, participant, now)
    match.version += 1
    result = {"operation_id": str(request.operation_id), "kind": kind, "version": match.version,
              "participant": participant.position, "number": question.number,
              "state": question.state}
    db.add(MatchCommand(match_id=match.id, operation_id=str(request.operation_id), payload=payload, result=result))
    project(db, match)
    response = {"operation": result, "state": public_state(match, now, owner.id)}
    db.commit()
    return response


def reconcile_for_user(db, owner):
    ids = list(db.scalars(select(PasapalabraMatch.id).where(
        ((PasapalabraMatch.owner_id == owner.id) | ((PasapalabraMatch.play_mode == "ONLINE") & PasapalabraMatch.participants.any(MatchParticipant.user_id == owner.id))), PasapalabraMatch.status == "RUNNING").order_by(PasapalabraMatch.id)))
    for match_id in ids:
        read_state(db, owner, match_id)
