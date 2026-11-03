from copy import deepcopy

import pytest
from sqlalchemy import select

from app.models import AnswerLog, Category, ContentBlock, GameSession, Question, Subject, Topic, User
from app.schemas.game import QuestionForGame
from app.schemas.game_snapshot import QuestionSnapshot


@pytest.fixture
def snapshot_bank(db, topic):
    subject = Subject(name="Original subject")
    db.add(subject)
    db.flush()
    block = ContentBlock(name="Original block", subject_id=subject.id)
    db.add(block)
    db.flush()
    category = Category(name="Original category", block_id=block.id)
    db.add(category)
    db.flush()
    trivial = Question(topic_id=topic.id, category=category, difficulty=2,
                       text="Original Trivial", options=["A", "B", "C", "D"],
                       correct_option_index=1, correct_answer="B")
    word = Question(topic_id=topic.id, category=category, difficulty=2,
                    question_type="PASAPALABRA", text="Empieza por L: original",
                    letter="L", exact_word="Luna", accepted_answers=["Satelite"], correct_answer="Luna")
    db.add_all([trivial, word])
    db.commit()
    return trivial, word, subject, block, category


def assert_no_solutions(value):
    if isinstance(value, dict):
        assert not {"question_snapshot", "correct_answer", "correct_option_index", "exact_word", "accepted_answers"} & value.keys()
        for child in value.values():
            assert_no_solutions(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_solutions(child)


@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
@pytest.mark.parametrize("correct", [True, False])
def test_mutating_bank_after_start_does_not_change_game(client, db, topic, test_user,
                                                       auth_headers, snapshot_bank, mode, correct):
    trivial, word, subject, block, category = snapshot_bank
    question = trivial if mode == "TRIVIAL" else word
    start = client.post(f"/game/start/{topic.id}", params={"mode": mode, "category_id": category.id,
                        "difficulty": 2}, headers=auth_headers)
    assert start.status_code == 201, start.text
    game = start.json()
    public = deepcopy(game["questions"])
    context = deepcopy(game["content_context"])
    assert_no_solutions(game)
    session = db.get(GameSession, game["session_id"])
    original_snapshot = deepcopy(session.question_snapshot)
    assert original_snapshot["questions"][0]["exact_word"] == question.exact_word
    original_topic_id = topic.id

    # Change every active field, including topic and mode, before submission.
    another_topic = Topic(name="Other topic")
    db.add(another_topic)
    db.flush()
    question.topic_id = another_topic.id
    question.text = "Modified bank"
    question.question_type = "PASAPALABRA" if mode == "TRIVIAL" else "TRIVIAL"
    question.options = ["New A", "New B", "New C", "New D"]
    question.correct_option_index = 0
    question.exact_word = "Mesa"
    question.accepted_answers = ["Changed synonym"]
    question.letter = "M"
    question.correct_answer = "New A"
    question.category_id = None
    question.difficulty = 4
    subject.name, block.name, category.name, topic.name = ("Renamed subject", "Renamed block", "Renamed category", "Renamed topic")
    db.commit()
    db.expire_all()
    session = db.get(GameSession, game["session_id"])
    assert session.question_snapshot == original_snapshot
    assert session.content_context == context
    assert context["questions"][0]["subject_name"] == "Original subject"
    assert context["questions"][0]["block_name"] == "Original block"
    # The same projection used at start still presents the original content.
    restored = QuestionSnapshot.model_validate(session.question_snapshot)
    assert [QuestionForGame.model_validate(q.model_dump()).model_dump() for q in restored.questions] == public
    unfinished = client.get(f"/game/history/{session.id}", headers=auth_headers).json()
    assert unfinished["answer_logs"] == []
    assert unfinished["question_content_source"] == "session_start"
    assert_no_solutions(unfinished)
    assert_no_solutions(client.get("/game/history", headers=auth_headers).json())
    assert_no_solutions(client.get("/game/progress", headers=auth_headers).json())
    next_game = client.post(f"/game/start/{another_topic.id}", params={"mode": question.question_type},
                            headers=auth_headers)
    assert next_game.status_code == 201
    assert next_game.json()["questions"][0]["text"] == "Modified bank"

    answer = {"question_id": question.id, "response_time_ms": 1200}
    answer.update({"selected_index": 1 if correct else 0} if mode == "TRIVIAL"
                  else {"text_answer": "  SATELITE  " if correct else "Mesa"})
    submitted = client.post(f"/game/submit/{session.id}", json={"answers": [answer]}, headers=auth_headers)
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()
    assert result["score"] == int(correct)
    correction = result["corrections"][0]
    assert correction["correct_option_index"] == (1 if mode == "TRIVIAL" else None)
    assert correction["exact_word"] == ("Luna" if mode == "PASAPALABRA" else None)
    history = client.get(f"/game/history/{session.id}", headers=auth_headers).json()
    assert history["topic_id"] == original_topic_id
    assert history["content_context"] == context
    saved = history["answer_logs"][0]
    assert saved["question_text"] == public[0]["text"]
    assert saved["options"] == public[0]["options"]
    assert saved["letter"] == public[0]["letter"]
    assert saved["accepted_answers"] == (["Satelite"] if mode == "PASAPALABRA" else None)
    assert saved["response_time_ms"] == 1200
    assert saved["is_correct"] is correct
    question.text = "Modified again after correction"
    question.exact_word = "Again"
    db.commit()
    assert client.get(f"/game/history/{session.id}", headers=auth_headers).json() == history
    marks = client.get("/game/progress", headers=auth_headers).json()["best_marks"]
    assert marks[0]["topic_name"] == context["topic_name"]
    assert marks[0]["topic_name_source"] == "historical"
    assert marks[0]["best_score"] == int(correct)
    assert client.post(f"/game/submit/{session.id}", json={"answers": [answer]}, headers=auth_headers).status_code == 409


@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
def test_legacy_open_games_fail_closed_and_completed_history_is_preserved(client, db, topic,
                                                                         test_user, auth_headers, snapshot_bank, mode):
    question = snapshot_bank[0 if mode == "TRIVIAL" else 1]
    session = GameSession(user_id=test_user.id, topic_id=topic.id, game_mode=mode, question_ids=[question.id])
    db.add(session)
    db.commit()
    answer = {"question_id": question.id, **({"selected_index": 1} if mode == "TRIVIAL" else {"text_answer": "Luna"})}
    response = client.post(f"/game/submit/{session.id}", json={"answers": [answer]}, headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LEGACY_SESSION_NO_SNAPSHOT"
    assert response.json()["detail"]["message"] == "Esta partida se inició con una versión anterior y ya no puede continuarse. Puedes empezar una nueva"
    db.refresh(session)
    assert session.question_snapshot is None and not session.is_completed and session.score == 0
    assert list(db.scalars(select(AnswerLog))) == []
    assert client.get(f"/game/history/{session.id}", headers=auth_headers).json()["question_content_source"] == "legacy"
    assert client.get(f"/game/history/{session.id}", headers=auth_headers).json()["continuation_error_code"] == "LEGACY_SESSION_NO_SNAPSHOT"
    # Legacy completed games only have the content captured at correction time.
    session.is_completed = True
    session.score = 1
    db.add(AnswerLog(game_session_id=session.id, question_id=question.id, question_text="Legacy saved text",
                     question_type=mode, options=["Saved A", "Saved B"] if mode == "TRIVIAL" else None,
                     selected_index=1 if mode == "TRIVIAL" else None,
                     correct_option_index=1 if mode == "TRIVIAL" else None,
                     exact_word="Saved word" if mode == "PASAPALABRA" else None, is_correct=True))
    db.commit()
    before = client.get(f"/game/history/{session.id}", headers=auth_headers).json()
    question.text = "Current text must not fill history"
    db.commit()
    assert client.get(f"/game/history/{session.id}", headers=auth_headers).json() == before
    assert before["answer_logs"][0]["question_text"] == "Legacy saved text"
    assert before["content_context"] is None
    assert before["question_content_source"] == "legacy"
    assert before["continuation_error_code"] is None


@pytest.mark.parametrize("damage", ["missing", "version", "id", "topic", "mode", "duplicate", "field", "missing_version"])
def test_snapshot_corruption_never_falls_back_to_bank(client, db, topic, auth_headers, snapshot_bank, damage):
    question = snapshot_bank[0]
    game = client.post(f"/game/start/{topic.id}", headers=auth_headers).json()
    session = db.get(GameSession, game["session_id"])
    snapshot = deepcopy(session.question_snapshot)
    if damage == "missing": snapshot["questions"] = []
    elif damage == "version": snapshot["version"] = 999
    elif damage == "duplicate": snapshot["questions"] *= 2
    elif damage == "field": del snapshot["questions"][0]["letter"]
    elif damage == "missing_version": del snapshot["version"]
    else: snapshot["questions"][0][{"id": "id", "topic": "topic_id", "mode": "question_type"}[damage]] = "PASAPALABRA" if damage == "mode" else 99999
    session.question_snapshot = snapshot
    db.commit()
    result = client.post(f"/game/submit/{session.id}", json={"answers": [{"question_id": question.id, "selected_index": 1}]}, headers=auth_headers)
    assert result.status_code == 409
    assert isinstance(result.json()["detail"], str)  # Other conflicts are not legacy-session errors.
    db.refresh(session)
    assert not session.is_completed and session.score == 0
    assert list(db.scalars(select(AnswerLog))) == []


def test_snapshot_solutions_are_private_even_with_an_unfinished_log(client, db, topic, test_user, auth_headers, snapshot_bank):
    game = client.post(f"/game/start/{topic.id}", headers=auth_headers).json()
    session = db.get(GameSession, game["session_id"])
    # Defensive serialization: an inconsistent partial legacy write must not leak a solution.
    db.add(AnswerLog(game_session_id=session.id, question_id=snapshot_bank[0].id,
                     question_text="Partial", question_type="TRIVIAL", exact_word="Secret", is_correct=True))
    other = User(name="Other", email="other-snapshot@example.com", hashed_password="unused")
    db.add(other)
    db.commit()
    detail = client.get(f"/game/history/{session.id}", headers=auth_headers).json()
    assert detail["answer_logs"] == []
    assert_no_solutions(detail)
    assert client.get(f"/game/history/{session.id}").status_code == 401
    session.user_id = other.id
    db.commit()
    assert client.get(f"/game/history/{session.id}", headers=auth_headers).status_code == 404
    assert client.post(f"/game/submit/{session.id}", headers=auth_headers,
                       json={"answers": [{"question_id": snapshot_bank[0].id, "selected_index": 1}]}).status_code == 403
