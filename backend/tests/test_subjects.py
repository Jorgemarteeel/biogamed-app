import pytest
from sqlalchemy import func, select

from app.models import GameSession, Question, Subject, Topic, UserRole


def subject_count(db):
    return db.scalar(select(func.count()).select_from(Subject))


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
def test_staff_can_list_create_and_read_same_subject(client, db, test_user, auth_headers, role):
    # The token was issued while this user was a student.
    test_user.role = role
    db.commit()
    assert client.get("/subjects", headers=auth_headers).json() == []

    created = client.post("/subjects", headers=auth_headers, json={
        "name": "  Bioinformática  ", "description": "Asignatura de prueba",
    })
    assert created.status_code == 201, created.text
    subject = created.json()
    assert subject == {
        "id": subject["id"], "name": "Bioinformática",
        "description": "Asignatura de prueba",
    }
    assert isinstance(subject["id"], int) and subject["id"] > 0
    assert db.get(Subject, subject["id"]).name == "Bioinformática"
    assert client.get("/subjects", headers=auth_headers).json() == [subject]


def test_subjects_require_authentication_and_current_staff_role(
    client, db, test_user, auth_headers,
):
    for headers in ({}, {"Authorization": "Bearer invalid-token"}):
        assert client.get("/subjects", headers=headers).status_code == 401
        assert client.post("/subjects", headers=headers, json={"name": "A"}).status_code == 401

    assert client.get("/subjects", headers=auth_headers).status_code == 403
    assert client.post("/subjects", headers=auth_headers, json={"name": "A"}).status_code == 403
    assert subject_count(db) == 0

    test_user.role = UserRole.TEACHER
    db.commit()
    assert client.get("/subjects", headers=auth_headers).status_code == 200
    assert client.post("/subjects", headers=auth_headers, json={"name": "A"}).status_code == 201

    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.get("/subjects", headers=auth_headers).status_code == 403
    assert client.post("/subjects", headers=auth_headers, json={"name": "B"}).status_code == 403
    assert subject_count(db) == 1


def test_subject_order_pagination_and_bounds(client, db, test_user, auth_headers):
    test_user.role = UserRole.TEACHER
    db.add_all([Subject(name=name) for name in ("Zeta", "Alfa", "Beta")])
    db.commit()

    all_subjects = client.get("/subjects", headers=auth_headers).json()
    assert [item["name"] for item in all_subjects] == ["Zeta", "Alfa", "Beta"]
    assert [item["id"] for item in all_subjects] == sorted(item["id"] for item in all_subjects)
    page = client.get("/subjects?skip=1&limit=1", headers=auth_headers)
    assert page.status_code == 200
    assert page.json() == [all_subjects[1]]
    assert client.get("/subjects?skip=3&limit=1", headers=auth_headers).json() == []
    for query in ("skip=-1", "limit=0", "limit=101"):
        assert client.get(f"/subjects?{query}", headers=auth_headers).status_code == 422


@pytest.mark.parametrize("payload", [
    {}, {"name": ""}, {"name": "  \t  "}, {"name": None},
    {"name": "x" * 256}, {"name": "A", "description": 42},
    {"name": "A", "role": "admin"}, {"name": "A", "owner_id": 1},
    {"name": "A", "permissions": ["all"]}, {"id": 3, "name": "A"},
])
def test_invalid_subject_does_not_create_row(client, db, test_user, auth_headers, payload):
    test_user.role = UserRole.TEACHER
    db.commit()
    response = client.post("/subjects", headers=auth_headers, json=payload)
    assert response.status_code == 422
    assert subject_count(db) == 0


def test_name_length_after_trim_and_optional_description(client, db, test_user, auth_headers):
    test_user.role = UserRole.ADMIN
    db.commit()
    response = client.post("/subjects", headers=auth_headers, json={
        "name": " " + "x" * 255 + " ",
    })
    assert response.status_code == 201
    assert response.json()["name"] == "x" * 255
    assert response.json()["description"] is None


def test_subject_creation_does_not_change_topics_questions_or_sessions(
    client, db, topic, test_user, auth_headers,
):
    question = Question(
        topic_id=topic.id, text="Pregunta existente", question_type="TRIVIAL",
        correct_answer="B", options=["A", "B", "C", "D"], correct_option_index=1,
    )
    db.add(question)
    db.flush()
    game = GameSession(user_id=test_user.id, topic_id=topic.id,
                       question_ids=[question.id], score=0, is_completed=False)
    db.add(game)
    db.commit()
    before = {
        model.__name__: db.scalar(select(func.count()).select_from(model))
        for model in (Topic, Question, GameSession)
    }
    original_question = (question.id, question.topic_id, question.text, question.correct_option_index)
    original_game = (game.id, game.topic_id, game.question_ids, game.is_completed)

    test_user.role = UserRole.TEACHER
    db.commit()
    response = client.post("/subjects", headers=auth_headers, json={"name": "Nueva"})
    assert response.status_code == 201
    assert before == {
        model.__name__: db.scalar(select(func.count()).select_from(model))
        for model in (Topic, Question, GameSession)
    }
    db.refresh(question)
    db.refresh(game)
    assert (question.id, question.topic_id, question.text, question.correct_option_index) == original_question
    assert (game.id, game.topic_id, game.question_ids, game.is_completed) == original_game
