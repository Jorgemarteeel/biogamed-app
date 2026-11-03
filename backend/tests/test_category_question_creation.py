import pytest
from sqlalchemy import func, select
from app.models import Category, ContentBlock, Question, Subject, UserRole


@pytest.fixture
def creation_path(db, topic):
    subject = Subject(name="Asignatura ficticia")
    db.add(subject)
    db.flush()
    block = ContentBlock(name="Bloque ficticio", subject_id=subject.id)
    db.add(block)
    db.flush()
    category = Category(name="Categoría ficticia", block_id=block.id)
    db.add(category)
    db.commit()
    return f"/subjects/{subject.id}/blocks/{block.id}/categories/{category.id}/questions"


def payload(topic, mode="TRIVIAL"):
    data = dict(text="Pista ficticia", topic_id=topic.id, question_type=mode)
    if mode == "TRIVIAL":
        data.update(options=["A", "B", "C", "D"], correct_option_index=1)
    else:
        data.update(letter="L", exact_word="Linfocito", accepted_answers=[" glóbulo blanco ", "GLÓBULO BLANCO"])
    return data


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
@pytest.mark.parametrize("difficulty", [None, 1, 2, 3, 4])
def test_create_persist_and_read(client, db, test_user, auth_headers, creation_path, topic, role, mode, difficulty):
    test_user.role = role
    db.commit()
    data = payload(topic, mode) | {"difficulty": difficulty}
    response = client.post(creation_path, json=data, headers=auth_headers)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["topic_id"] == topic.id
    assert created["topic"]["name"] == topic.name
    assert created["difficulty"] == difficulty
    stored = db.get(Question, created["id"])
    assert stored.category_id == created["category_id"]
    assert stored.correct_answer == ("B" if mode == "TRIVIAL" else "Linfocito")
    if mode == "PASAPALABRA":
        assert created["accepted_answers"] == ["glóbulo blanco"]
    assert client.get(creation_path, headers=auth_headers).json() == [created]


def test_permissions_hierarchy_topic_and_legacy(client, db, test_user, auth_headers, creation_path, topic):
    data = payload(topic)
    assert client.post(creation_path, json=data).status_code == 401
    assert client.post(creation_path, json=data, headers=auth_headers).status_code == 403
    test_user.role = UserRole.TEACHER
    db.commit()
    for segment in (1, 3, 5):
        parts = creation_path.split("/")
        parts[segment + 1] = "99999"
        assert client.post("/".join(parts), json=data, headers=auth_headers).status_code == 404
    other_subject = Subject(name="Otra asignatura")
    db.add(other_subject)
    db.commit()
    parts = creation_path.split("/")
    parts[2] = str(other_subject.id)
    assert client.post("/".join(parts), json=data, headers=auth_headers).status_code == 404
    original_parts = creation_path.split("/")
    other_block = ContentBlock(name="Otro bloque", subject_id=int(original_parts[2]))
    db.add(other_block)
    db.flush()
    other_category = Category(name="Categoría ajena", block_id=other_block.id)
    db.add(other_category)
    db.commit()
    for position, wrong_id in ((4, other_block.id), (6, other_category.id)):
        parts = original_parts.copy()
        parts[position] = str(wrong_id)
        assert client.post("/".join(parts), json=data, headers=auth_headers).status_code == 404
    for override in ({"topic_id": 99999}, {"category_id": 1}, {"category_id": None}, {"extra": 1}):
        response = client.post(creation_path, json=data | override, headers=auth_headers)
        assert response.status_code == (404 if "topic_id" in override else 422)
    assert db.scalar(select(func.count()).select_from(Question)) == 0
    legacy = client.post("/questions/", json=data, headers=auth_headers)
    assert legacy.status_code == 201
    assert db.get(Question, legacy.json()["id"]).category_id is None
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.post(creation_path, json=data, headers=auth_headers).status_code == 403


@pytest.mark.parametrize("mode,changes", [
    ("TRIVIAL", {"text": "   "}), ("TRIVIAL", {"options": ["", "B", "C", "D"]}),
    ("TRIVIAL", {"options": [" ", "B", "C", "D"]}), ("TRIVIAL", {"options": ["A"]}),
    ("TRIVIAL", {"correct_option_index": None}), ("TRIVIAL", {"correct_option_index": 4}),
    ("TRIVIAL", {"letter": "L"}), ("TRIVIAL", {"exact_word": "Linfocito"}),
    ("TRIVIAL", {"accepted_answers": ["A"]}),
    ("PASAPALABRA", {"options": ["A", "B", "C", "D"]}),
    ("PASAPALABRA", {"correct_option_index": 0}),
    ("PASAPALABRA", {"letter": "1"}), ("PASAPALABRA", {"letter": "AB"}),
    ("PASAPALABRA", {"exact_word": " "}), ("PASAPALABRA", {"exact_word": "Macrófago"}),
    ("PASAPALABRA", {"text": "Contiene la letra L", "exact_word": "Macrófago"}),
    ("PASAPALABRA", {"accepted_answers": [" "]}),
    ("PASAPALABRA", {"accepted_answers": ["x"] * 31}),
    ("PASAPALABRA", {"accepted_answers": ["x" * 256]}),
])
def test_invalid_modalities_do_not_write(client, db, test_user, auth_headers, creation_path, topic, mode, changes):
    test_user.role = UserRole.TEACHER
    db.commit()
    response = client.post(creation_path, json=payload(topic, mode) | changes, headers=auth_headers)
    assert response.status_code == 422, response.text
    assert db.scalar(select(func.count()).select_from(Question)) == 0


@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
@pytest.mark.parametrize("difficulty", [0, 5, True, 2.0, "2"])
def test_invalid_difficulty(client, db, test_user, auth_headers, creation_path, topic, mode, difficulty):
    test_user.role = UserRole.TEACHER
    db.commit()
    assert client.post(creation_path, json=payload(topic, mode) | {"difficulty": difficulty}, headers=auth_headers).status_code == 422
    assert db.scalar(select(func.count()).select_from(Question)) == 0


def test_contains_and_omitted_difficulty(client, db, test_user, auth_headers, creation_path, topic):
    test_user.role = UserRole.TEACHER
    db.commit()
    data = payload(topic, "PASAPALABRA") | {"text": "Contiene la letra L: pista ficticia", "exact_word": "Glóbulo"}
    result = client.post(creation_path, json=data, headers=auth_headers)
    assert result.status_code == 201, result.text
    assert result.json()["difficulty"] is None
