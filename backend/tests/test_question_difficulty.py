import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import Question, UserRole


@pytest.fixture
def staff_headers(db, test_user, auth_headers):
    test_user.role = UserRole.TEACHER
    db.commit()
    return auth_headers


def question_payload(topic_id, mode):
    payload = {"topic_id": topic_id, "text": "Empieza por A: arteria principal.", "question_type": mode}
    if mode == "TRIVIAL":
        payload.update(options=["Aorta", "Vena", "Corazón", "Pulmón"], correct_option_index=0)
    else:
        payload.update(letter="A", exact_word="Aorta")
    return payload


@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
@pytest.mark.parametrize("difficulty", ["omitted", None, 1, 2, 3, 4])
def test_create_and_read_optional_difficulty(client, db, topic, staff_headers, mode, difficulty):
    payload = question_payload(topic.id, mode)
    if difficulty != "omitted":
        payload["difficulty"] = difficulty
    expected = None if difficulty == "omitted" else difficulty
    response = client.post("/questions/", headers=staff_headers, json=payload)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["difficulty"] == expected
    db.expire_all()
    assert db.get(Question, created["id"]).difficulty == expected
    bank = client.get(f"/questions/topic/{topic.id}", headers=staff_headers)
    assert bank.status_code == 200, bank.text
    assert bank.json() == [created]
    if mode == "PASAPALABRA":
        updated = client.patch(
            f"/questions/{created['id']}/accepted-answers",
            headers=staff_headers, json={"accepted_answers": []},
        )
        assert updated.status_code == 200
        assert updated.json()["difficulty"] == expected


@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
@pytest.mark.parametrize("difficulty", [True, False, -1, 0, 5, 1.0, 2.5, "1", "4", "", [], {}])
def test_api_rejects_non_integer_or_out_of_range_difficulty(
    client, db, topic, staff_headers, mode, difficulty,
):
    payload = question_payload(topic.id, mode)
    payload["difficulty"] = difficulty
    response = client.post("/questions/", headers=staff_headers, json=payload)
    assert response.status_code == 422, response.text
    assert any(error["loc"] == ["body", "difficulty"] for error in response.json()["detail"])
    assert db.query(Question).count() == 0


@pytest.mark.parametrize("difficulty", [-1, 0, 5])
def test_database_rejects_out_of_range_difficulty(db, topic, difficulty):
    # Bypass both Pydantic and the ORM to exercise the database CHECK constraint.
    with pytest.raises(IntegrityError, match="ck_question_difficulty"):
        db.execute(text(
            "INSERT INTO questions (text,correct_answer,topic_id,difficulty) "
            "VALUES ('Question','Answer',:topic,:difficulty)"
        ), {"topic": topic.id, "difficulty": difficulty})
    db.rollback()
    assert db.query(Question).count() == 0


@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
def test_difficulty_does_not_change_game_selection_scoring_or_history(
    client, db, topic, staff_headers, mode,
):
    questions = []
    for difficulty in [None, 1, 4]:
        payload = question_payload(topic.id, mode)
        payload["difficulty"] = difficulty
        response = client.post("/questions/", headers=staff_headers, json=payload)
        assert response.status_code == 201, response.text
        questions.append(response.json())
    started = client.post(f"/game/start/{topic.id}?mode={mode}", headers=staff_headers)
    assert started.status_code == 201, started.text
    game = started.json()
    assert {q["id"] for q in game["questions"]} == {q["id"] for q in questions}
    assert all("difficulty" not in q for q in game["questions"])
    answers = [{"question_id": q["id"], **(
        {"selected_index": 0} if mode == "TRIVIAL" else {"text_answer": "Aorta"}
    )} for q in questions]
    result = client.post(f"/game/submit/{game['session_id']}", headers=staff_headers,
                         json={"answers": answers})
    assert result.status_code == 200, result.text
    assert result.json()["score"] == result.json()["total_questions"] == 3
    history = client.get(f"/game/history/{game['session_id']}", headers=staff_headers)
    assert history.status_code == 200
    assert history.json()["is_completed"] is True
    assert len(history.json()["answer_logs"]) == 3
    assert all(log["is_correct"] for log in history.json()["answer_logs"])
