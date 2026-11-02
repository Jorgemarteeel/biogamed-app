import pytest
from sqlalchemy import func, select

from app.models import Category, ContentBlock, Question, Subject, UserRole


@pytest.fixture
def hierarchy(db):
    first, second = Subject(name="Primera"), Subject(name="Segunda")
    db.add_all([first, second])
    db.flush()
    blocks = [ContentBlock(subject_id=first.id, name="Uno"),
              ContentBlock(subject_id=first.id, name="Dos"),
              ContentBlock(subject_id=second.id, name="Ajeno")]
    db.add_all(blocks)
    db.commit()
    return first, second, blocks


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
def test_staff_detail_create_and_separation(client, db, hierarchy, test_user, auth_headers, role):
    first, _, blocks = hierarchy
    test_user.role = role
    db.commit()
    url = f"/subjects/{first.id}/blocks/{blocks[0].id}"
    detail = client.get(url, headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["subject"]["name"] == "Primera"
    assert client.get(url + "/categories", headers=auth_headers).json() == []
    created = client.post(url + "/categories", headers=auth_headers,
                          json={"name": "  Categoría  ", "description": "Origen"})
    assert created.status_code == 201, created.text
    item = created.json()
    assert item == {"id": item["id"], "block_id": blocks[0].id,
                    "name": "Categoría", "description": "Origen"}
    assert db.get(Category, item["id"]).block_id == blocks[0].id
    assert client.get(url + "/categories", headers=auth_headers).json() == [item]
    assert client.get(f"/subjects/{first.id}/blocks/{blocks[1].id}/categories",
                      headers=auth_headers).json() == []


def test_auth_current_role_and_references(client, db, hierarchy, test_user, auth_headers):
    first, second, blocks = hierarchy
    url = f"/subjects/{first.id}/blocks/{blocks[0].id}"
    for suffix in ("", "/categories"):
        assert client.get(url + suffix).status_code == 401
        assert client.get(url + suffix, headers=auth_headers).status_code == 403
    assert client.post(url + "/categories", json={"name": "A"}).status_code == 401
    assert client.post(url + "/categories", headers=auth_headers,
                       json={"name": "A"}).status_code == 403
    test_user.role = UserRole.TEACHER
    db.commit()
    assert client.get(url, headers=auth_headers).status_code == 200
    wrong = f"/subjects/{second.id}/blocks/{blocks[0].id}"
    for target in (wrong, f"/subjects/{first.id}/blocks/{blocks[2].id}",
                   f"/subjects/{first.id}/blocks/9999", f"/subjects/9999/blocks/{blocks[0].id}"):
        assert client.get(target, headers=auth_headers).status_code == 404
        assert client.get(target + "/categories", headers=auth_headers).status_code == 404
        assert client.post(target + "/categories", headers=auth_headers,
                           json={"name": "A"}).status_code == 404
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.get(url + "/categories", headers=auth_headers).status_code == 403


def test_invalid_payload_and_unplaced_categories_untouched(client, db, hierarchy, topic,
                                                            test_user, auth_headers):
    first, _, blocks = hierarchy
    unplaced = Category(name="Origen sin bloque")
    question = Question(topic_id=topic.id, text="Q", correct_answer="A", category=unplaced)
    db.add_all([unplaced, question])
    test_user.role = UserRole.TEACHER
    db.commit()
    old_id, old_question_id = unplaced.id, question.id
    url = f"/subjects/{first.id}/blocks/{blocks[0].id}/categories"
    for body in ({}, {"name": "  "}, {"name": "x" * 256},
                 {"name": "A", "block_id": blocks[1].id},
                 {"name": "A", "subject_id": first.id}, {"name": "A", "role": "admin"},
                 {"name": "A", "description": 12}):
        assert client.post(url, headers=auth_headers, json=body).status_code == 422
    assert db.scalar(select(func.count()).select_from(Category)) == 1
    assert client.post(url, headers=auth_headers,
                       json={"name": " " + "x" * 255 + " "}).status_code == 201
    db.refresh(unplaced)
    db.refresh(question)
    assert unplaced.id == old_id and unplaced.block_id is None
    assert question.id == old_question_id and question.category_id == old_id
    assert all(item["id"] != old_id for item in client.get(url, headers=auth_headers).json())


def test_order_and_pagination(client, db, hierarchy, test_user, auth_headers):
    first, _, blocks = hierarchy
    db.add_all([Category(block_id=blocks[0].id, name=name) for name in ("Z", "A", "B")])
    db.add(Category(block_id=blocks[1].id, name="Otro"))
    test_user.role = UserRole.ADMIN
    db.commit()
    url = f"/subjects/{first.id}/blocks/{blocks[0].id}/categories"
    items = client.get(url, headers=auth_headers).json()
    assert [item["name"] for item in items] == ["Z", "A", "B"]
    assert [item["id"] for item in items] == sorted(item["id"] for item in items)
    assert client.get(url + "?skip=1&limit=1", headers=auth_headers).json() == [items[1]]
    assert client.get(url + "?skip=3&limit=1", headers=auth_headers).json() == []
    for query in ("skip=-1", "limit=0", "limit=101"):
        assert client.get(url + "?" + query, headers=auth_headers).status_code == 422
