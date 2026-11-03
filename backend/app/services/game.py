from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import AnswerLog, Category, GameSession, Question, Topic, User
from app.utils.answers import is_accepted_answer
from app.services.game_questions import selectable_questions
from app.services.game_progress import get_personal_best_marks
from app.schemas.game import (
    AnswerCorrection, GameAvailabilityResponse, GameResultResponse, GameSessionStartResponse,
    QuestionForGame, UserAnswer,
)
from app.schemas.game_snapshot import QuestionSnapshot, StoredQuestion


def _session_questions(session: GameSession) -> list[StoredQuestion]:
    if session.question_snapshot is None:
        raise HTTPException(409, "Esta partida antigua no conserva las preguntas al inicio. Comienza una nueva partida.")
    try:
        snapshot = QuestionSnapshot.model_validate(session.question_snapshot)
    except ValidationError:
        raise HTTPException(409, "La copia de preguntas de esta partida no es válida.") from None
    ids = [q.id for q in snapshot.questions]
    if (ids != session.question_ids or len(set(ids)) != len(ids)
            or any(q.topic_id != session.topic_id or q.question_type != session.game_mode
                   for q in snapshot.questions)):
        raise HTTPException(409, "La copia de preguntas de esta partida no es válida.")
    return snapshot.questions


def _classification(question: Question) -> dict:
    category = question.category
    block = category.block if category else None
    subject = block.subject if block else None
    return {"question_id": question.id, "category_id": question.category_id,
            "category_name": category.name if category else None,
            "difficulty": question.difficulty,
            "block_id": block.id if block else None, "block_name": block.name if block else None,
            "subject_id": subject.id if subject else None, "subject_name": subject.name if subject else None}


def start_game_session(
    db: Session, current_user: User, topic_id: int, game_mode: str = "TRIVIAL",
    category_id: int | None = None, difficulty: int | None = None,
    difficulty_unknown: bool = False,
) -> GameSessionStartResponse:
    statement = selectable_questions(topic_id, game_mode, category_id, difficulty,
                                     difficulty_unknown)
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "La temática no existe.")
    questions = list(db.scalars(statement.order_by(func.random()).limit(10)))
    if not questions:
        raise HTTPException(409, "No hay preguntas disponibles para esta combinación de filtros.")
    snapshot = QuestionSnapshot(version=1, questions=[StoredQuestion.model_validate(q) for q in questions])
    # Project explicitly into the public schema; the storage schema includes solutions.
    public_questions = [QuestionForGame.model_validate(q.model_dump()) for q in snapshot.questions]
    content_context = {
        "topic_name": topic.name,
        "selection": {
            "category_id": category_id,
            "category_name": questions[0].category.name if category_id is not None else None,
            "difficulty": difficulty, "difficulty_unknown": difficulty_unknown,
        },
        "questions": [_classification(q) for q in questions],
    }
    session = GameSession(
        user_id=current_user.id, topic_id=topic_id, game_mode=game_mode,
        question_ids=[q.id for q in questions], content_context=content_context,
        question_snapshot=snapshot.model_dump(),
        is_completed=False, score=0,
    )
    try:
        db.add(session)
        db.flush()
        result = GameSessionStartResponse(
            session_id=session.id, topic_id=topic_id, questions=public_questions,
            content_context=content_context,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def get_game_availability(db: Session, topic_id: int, game_mode: str = "TRIVIAL",
                          category_id: int | None = None, difficulty: int | None = None,
                          difficulty_unknown: bool = False) -> GameAvailabilityResponse:
    statement = selectable_questions(topic_id, game_mode, category_id, difficulty,
                                     difficulty_unknown)
    if db.get(Topic, topic_id) is None:
        raise HTTPException(404, "La temática no existe.")
    counts = db.execute(
        statement.with_only_columns(
            Question.category_id, Category.name, Question.difficulty,
            func.count(Question.id), maintain_column_froms=True,
        ).outerjoin(Category, Question.category_id == Category.id)
        .group_by(Question.category_id, Category.name, Question.difficulty)
        .order_by(Question.category_id, Question.difficulty)
    ).all()
    return GameAvailabilityResponse(
        topic_id=topic_id, game_mode=game_mode,
        total_questions=sum(row[3] for row in counts),
        combinations=[{"category_id": row[0], "category_name": row[1],
                       "difficulty": row[2], "count": row[3]}
                      for row in counts],
    )


def submit_game_session(
    db: Session, current_user: User, session_id: int, answers: list[UserAnswer]
) -> GameResultResponse:
    try:
        session = db.scalar(
            select(GameSession).where(GameSession.id == session_id).with_for_update()
        )
        if session is None:
            raise HTTPException(404, "La sesión no existe.")
        if session.user_id != current_user.id:
            raise HTTPException(403, "La sesión pertenece a otro usuario.")
        if session.is_completed:
            raise HTTPException(409, "La sesión ya está completada.")
        if session.game_mode not in {"TRIVIAL", "PASAPALABRA"}:
            raise HTTPException(409, "El modo de la sesión no es válido.")
        submitted_ids = [answer.question_id for answer in answers]
        if (len(set(submitted_ids)) != len(submitted_ids)
                or set(submitted_ids) != set(session.question_ids)):
            raise HTTPException(422, "Envía una respuesta por cada pregunta de la sesión, sin duplicados.")
        questions = {q.id: q for q in _session_questions(session)}
        corrections = []
        logs = []
        for answer in answers:
            question = questions.get(answer.question_id)
            if (question is None or question.topic_id != session.topic_id
                    or question.question_type != session.game_mode):
                raise HTTPException(409, "Una pregunta de la sesión ya no está disponible.")
            if session.game_mode == "TRIVIAL":
                if (not question.options or question.correct_option_index is None
                        or not 0 <= question.correct_option_index < len(question.options)):
                    raise HTTPException(409, "Una pregunta de la sesión ya no está disponible.")
                if (answer.selected_index is None
                        or not 0 <= answer.selected_index < len(question.options)):
                    raise HTTPException(422, "TRIVIAL requiere un selected_index válido.")
                correction = AnswerCorrection(
                    question_id=question.id, selected_index=answer.selected_index,
                    correct_option_index=question.correct_option_index,
                    is_correct=answer.selected_index == question.correct_option_index,
                )
            else:
                if not question.exact_word or not question.exact_word.strip():
                    raise HTTPException(409, "Una pregunta de la sesión ya no está disponible.")
                if answer.text_answer is None:
                    raise HTTPException(422, "PASAPALABRA requiere text_answer.")
                correction = AnswerCorrection(
                    question_id=question.id, text_answer=answer.text_answer,
                    exact_word=question.exact_word,
                    is_correct=is_accepted_answer(
                        answer.text_answer, question.exact_word, question.accepted_answers,
                    ),
                )
            corrections.append(correction)
            logs.append(AnswerLog(
                game_session_id=session.id, question_id=question.id,
                question_text=question.text, question_type=session.game_mode,
                options=list(question.options) if session.game_mode == "TRIVIAL" else None,
                letter=question.letter if session.game_mode == "PASAPALABRA" else None,
                selected_index=correction.selected_index, text_answer=correction.text_answer,
                correct_option_index=correction.correct_option_index,
                exact_word=correction.exact_word, is_correct=correction.is_correct,
                accepted_answers=list(question.accepted_answers or []) if session.game_mode == "PASAPALABRA" else None,
                response_time_ms=answer.response_time_ms,
            ))
        score = sum(c.is_correct for c in corrections)
        # The conditional update also prevents double submissions without row locks.
        updated = db.execute(update(GameSession).where(
            GameSession.id == session_id, GameSession.is_completed.is_(False),
        ).values(score=score, is_completed=True))
        if updated.rowcount != 1:
            raise HTTPException(409, "La sesión ya está completada.")
        db.add_all(logs)
        result = GameResultResponse(
            score=score, total_questions=len(session.question_ids), corrections=corrections
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def get_game_history(db: Session, current_user: User, skip: int, limit: int):
    return list(db.scalars(select(GameSession).where(
        GameSession.user_id == current_user.id,
    ).order_by(GameSession.created_at.desc(), GameSession.id.desc()).offset(skip).limit(limit)))


def get_game_progress(db: Session, current_user: User):
    rows = db.execute(select(
        GameSession.game_mode,
        GameSession.is_completed,
        func.count(GameSession.id),
    ).where(GameSession.user_id == current_user.id).group_by(
        GameSession.game_mode, GameSession.is_completed,
    )).all()
    by_mode = {mode: {"started": 0, "completed": 0, "unfinished": 0}
               for mode in ("TRIVIAL", "PASAPALABRA")}
    totals = {"started": 0, "completed": 0, "unfinished": 0}
    for mode, completed, count in rows:
        status = "completed" if completed else "unfinished"
        by_mode[mode]["started"] += count
        by_mode[mode][status] += count
        totals["started"] += count
        totals[status] += count
    return {**totals, "by_mode": by_mode,
            "best_marks": get_personal_best_marks(db, current_user)}


def get_game_history_detail(db: Session, current_user: User, session_id: int):
    session = db.scalar(select(GameSession).where(
        GameSession.id == session_id, GameSession.user_id == current_user.id,
    ))
    if session is None:
        raise HTTPException(404, "La sesión no existe.")
    return session
