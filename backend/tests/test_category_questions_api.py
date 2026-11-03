import pytest

from app.models import Category, ContentBlock, Question, Subject, Topic, UserRole


@pytest.fixture
def category_bank(db):
    subjects = [Subject(name="Docencia"), Subject(name="Otra")]
    db.add_all(subjects)
    db.flush()
    blocks = [ContentBlock(subject_id=subjects[0].id, name="Primero"),
              ContentBlock(subject_id=subjects[0].id, name="Segundo"),
              ContentBlock(subject_id=subjects[1].id, name="Ajeno")]
    db.add_all(blocks)
    db.flush()
    categories = [Category(block_id=blocks[0].id, name="Inmunología"),
                  Category(block_id=blocks[1].id, name="Otra categoría"),
                  Category(block_id=blocks[0].id, name="Vacía")]
    db.add_all(categories)
    topic = Topic(name="Temática heredada")
    db.add(topic)
    db.flush()
    questions = []
    for index in range(14):
        questions.append(Question(
            topic_id=topic.id, category_id=categories[0].id,
            text=f"Enunciado {index}", question_type="TRIVIAL",
            options=["A", "B", "C", "D"], correct_option_index=1,
            correct_answer="B", difficulty=2 if index < 12 else None,
        ))
    questions.append(Question(
        topic_id=topic.id, category_id=categories[0].id,
        text="Empieza por L", question_type="PASAPALABRA",
        letter="L", exact_word="Linfocito", accepted_answers=["Linfocitos"],
        correct_answer="Linfocito", difficulty=None,
    ))
    questions.append(Question(
        topic_id=topic.id, category_id=categories[1].id,
        text="Pregunta ajena", question_type="TRIVIAL",
        options=["X", "Y", "Z", "W"], correct_option_index=0,
        correct_answer="X", difficulty=2,
    ))
    db.add_all(questions)
    db.commit()
    return subjects, blocks, categories, questions


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
def test_staff_can_read_detail_and_solutions(client, db, test_user, auth_headers,
                                             category_bank, role):
    subjects, blocks, categories, questions = category_bank
    test_user.role = role
    db.commit()
    base = f"/subjects/{subjects[0].id}/blocks/{blocks[0].id}/categories/{categories[0].id}"
    detail = client.get(base, headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["block"]["subject"]["name"] == "Docencia"
    assert detail.json()["name"] == "Inmunología"
    items = client.get(base + "/questions?skip=0&limit=100", headers=auth_headers)
    assert items.status_code == 200, items.text
    assert [item["id"] for item in items.json()] == sorted(q.id for q in questions[:15])
    assert all(item["category_id"] == categories[0].id for item in items.json())
    assert items.json()[0]["correct_option_index"] == 1
    assert items.json()[0]["topic"]["name"] == "Temática heredada"
    assert items.json()[-1]["exact_word"] == "Linfocito"
    assert items.json()[-1]["accepted_answers"] == ["Linfocitos"]
    empty = f"/subjects/{subjects[0].id}/blocks/{blocks[0].id}/categories/{categories[2].id}"
    assert client.get(empty, headers=auth_headers).status_code == 200
    assert client.get(empty + "/questions", headers=auth_headers).json() == []


def test_auth_uses_current_role_and_wrong_hierarchy_is_hidden(client, db, test_user,
                                                               auth_headers, category_bank):
    subjects, blocks, categories, _ = category_bank
    base = f"/subjects/{subjects[0].id}/blocks/{blocks[0].id}/categories/{categories[0].id}"
    for path in (base, base + "/questions"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=auth_headers).status_code == 403
    test_user.role = UserRole.TEACHER
    db.commit()
    assert client.get(base, headers=auth_headers).status_code == 200
    wrong = [
        f"/subjects/{subjects[1].id}/blocks/{blocks[0].id}/categories/{categories[0].id}",
        f"/subjects/{subjects[0].id}/blocks/{blocks[1].id}/categories/{categories[0].id}",
        f"/subjects/{subjects[0].id}/blocks/{blocks[0].id}/categories/{categories[1].id}",
        f"/subjects/{subjects[0].id}/blocks/{blocks[0].id}/categories/99999",
    ]
    for path in wrong:
        assert client.get(path, headers=auth_headers).status_code == 404
        assert client.get(path + "/questions", headers=auth_headers).status_code == 404
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.get(base + "/questions", headers=auth_headers).status_code == 403


def test_filters_and_server_pagination(client, db, test_user, auth_headers, category_bank):
    subjects, blocks, categories, questions = category_bank
    test_user.role = UserRole.ADMIN
    db.commit()
    base = f"/subjects/{subjects[0].id}/blocks/{blocks[0].id}/categories/{categories[0].id}/questions"
    def ids(query):
        response = client.get(base + query, headers=auth_headers)
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()]
    assert ids("?mode=TRIVIAL&difficulty=2&skip=10&limit=2") == [q.id for q in questions[10:12]]
    assert ids("?mode=TRIVIAL&difficulty_unknown=true") == [q.id for q in questions[12:14]]
    assert ids("?mode=PASAPALABRA&difficulty_unknown=true") == [questions[14].id]
    assert ids("?mode=PASAPALABRA&difficulty=2") == []
    assert ids("?limit=2") == [q.id for q in questions[:2]]
    for query in ("?mode=OTRO", "?difficulty=0", "?difficulty=5", "?skip=-1",
                  "?limit=0", "?limit=101", "?difficulty=2&difficulty_unknown=true"):
        assert client.get(base + query, headers=auth_headers).status_code == 422
