import pytest

from app.models import AnswerLog, GameSession, Question, User


@pytest.mark.parametrize(
    "selected_index, expected_score",
    [(2, 1), (0, 0)],
    ids=["correct-answer", "incorrect-answer"],
)
def test_game_engine_trivial(client, db, topic, auth_headers, selected_index, expected_score):
    question = Question(
        text="Which organ pumps blood?",
        topic_id=topic.id,
        question_type="TRIVIAL",
        options=["Lung", "Liver", "Heart", "Kidney"],
        correct_option_index=2,
        correct_answer="Heart",
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    start = client.post(f"/game/start/{topic.id}", headers=auth_headers)
    assert start.status_code == 201, start.text
    game = start.json()
    assert [item["id"] for item in game["questions"]] == [question.id]
    assert "correct_option_index" not in game["questions"][0]

    response = client.post(
        f"/game/submit/{game['session_id']}",
        headers=auth_headers,
        json={"answers": [{"question_id": question.id, "selected_index": selected_index, "response_time_ms": 1500}]},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["score"] == expected_score
    assert result["total_questions"] == 1
    assert len(result["corrections"]) == 1
    correction = result["corrections"][0]
    assert correction["question_id"] == question.id
    assert correction["is_correct"] is bool(expected_score)
    assert correction["correct_option_index"] == 2
    db.expire_all()
    session = db.get(GameSession, game["session_id"])
    assert session.is_completed is True
    assert session.score == expected_score
    assert len(session.answer_logs) == 1
    log = session.answer_logs[0]
    assert log.selected_index == selected_index
    assert log.is_correct is bool(expected_score)
    assert log.response_time_ms == 1500
    assert log.question is question
    assert session in session.user.game_sessions
    assert log in question.answer_logs

    # Editing the bank must not rewrite what was answered or its correction.
    question.text = "Changed question"
    question.options = ["New A", "New B", "New C", "New D"]
    question.correct_option_index = 0
    db.commit()
    history = client.get(f"/game/history/{session.id}", headers=auth_headers)
    assert history.status_code == 200
    saved = history.json()["answer_logs"][0]
    assert saved["question_text"] == "Which organ pumps blood?"
    assert saved["options"] == ["Lung", "Liver", "Heart", "Kidney"]
    assert saved["correct_option_index"] == 2
    repeat = client.post(f"/game/submit/{session.id}", headers=auth_headers,
                         json={"answers": [{"question_id": question.id, "selected_index": 0}]})
    assert repeat.status_code == 409
    assert db.query(AnswerLog).count() == 1


@pytest.mark.parametrize("text_answer", ["Aorta", "  aORTA  ", "\tAORTA\n"])
def test_game_engine_pasapalabra(client, db, topic, auth_headers, text_answer):
    question = Question(
        text="Starts with A: the main artery leaving the heart.",
        topic_id=topic.id,
        question_type="PASAPALABRA",
        letter="A",
        exact_word="Aorta",
        correct_answer="Aorta",
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    start = client.post(
        f"/game/start/{topic.id}",
        params={"mode": "PASAPALABRA"},
        headers=auth_headers,
    )
    assert start.status_code == 201, start.text
    game = start.json()
    assert [item["id"] for item in game["questions"]] == [question.id]
    assert game["questions"][0]["letter"] == "A"
    assert "exact_word" not in game["questions"][0]

    response = client.post(
        f"/game/submit/{game['session_id']}",
        headers=auth_headers,
        json={"answers": [{"question_id": question.id, "text_answer": text_answer}]},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["score"] == 1
    assert result["total_questions"] == 1
    assert len(result["corrections"]) == 1
    correction = result["corrections"][0]
    assert correction["question_id"] == question.id
    assert correction["is_correct"] is True
    assert correction["exact_word"] == "Aorta"
    db.expire_all()
    session = db.get(GameSession, game["session_id"])
    assert session.is_completed is True
    assert session.score == 1
    assert len(session.answer_logs) == 1
    log = session.answer_logs[0]
    assert log.text_answer == text_answer
    assert log.exact_word == "Aorta"
    assert log.letter == "A"
    assert log.response_time_ms is None
    assert log.is_correct is True


def test_history_is_private(client, db, topic, auth_headers, test_user):
    other = User(name="Other", email="other@example.com", hashed_password="unused")
    db.add(other)
    db.flush()
    own = GameSession(user_id=test_user.id, topic_id=topic.id, question_ids=[])
    foreign = GameSession(user_id=other.id, topic_id=topic.id, question_ids=[])
    db.add_all([own, foreign])
    db.commit()
    response = client.get("/game/history", headers=auth_headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own.id]
    assert client.get(f"/game/history/{foreign.id}", headers=auth_headers).status_code == 404
    assert client.get("/game/history").status_code == 401
    assert client.get(f"/game/history/{own.id}").status_code == 401
    assert client.get("/game/history?limit=0", headers=auth_headers).status_code == 422
    assert client.get("/game/history?skip=1", headers=auth_headers).json() == []
    # Pre-existing completed games have no fabricated answer history.
    own.is_completed = True
    db.commit()
    assert client.get(f"/game/history/{own.id}", headers=auth_headers).json()["answer_logs"] == []


def test_history_and_score_roll_back_together(db, topic, test_user):
    from sqlalchemy import event
    from app.schemas.game import UserAnswer
    from app.services.game import start_game_session, submit_game_session

    question = Question(text="Question", topic_id=topic.id, options=["A", "B", "C", "D"],
                        correct_answer="A", correct_option_index=0)
    db.add(question)
    db.commit()
    game = start_game_session(db, test_user, topic.id)
    def fail_insert(*args):
        raise RuntimeError("history write failed")
    event.listen(AnswerLog, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="history write failed"):
            submit_game_session(db, test_user, game.session_id,
                                [UserAnswer(question_id=question.id, selected_index=0)])
    finally:
        event.remove(AnswerLog, "before_insert", fail_insert)
    session = db.get(GameSession, game.session_id)
    assert session.is_completed is False
    assert session.score == 0
    assert db.query(AnswerLog).count() == 0
