import pytest
from sqlalchemy import func, select

from app.models import ContentBlock, Subject, UserRole


@pytest.fixture
def subjects(db):
    first, second = Subject(name="Zeta"), Subject(name="Alfa")
    db.add_all([first, second])
    db.commit()
    return first, second


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
def test_staff_can_create_and_list_blocks(client, db, subjects, test_user, auth_headers, role):
    first, second = subjects
    test_user.role = role
    db.commit()
    assert client.get(f"/subjects/{first.id}", headers=auth_headers).json()["name"] == "Zeta"
    assert client.get(f"/subjects/{first.id}/blocks", headers=auth_headers).json() == []
    result = client.post(f"/subjects/{first.id}/blocks", headers=auth_headers,
                         json={"name": "  Bloque uno  ", "description": "Base"})
    assert result.status_code == 201, result.text
    block = result.json()
    assert block == {"id": block["id"], "subject_id": first.id,
                     "name": "Bloque uno", "description": "Base"}
    assert db.get(ContentBlock, block["id"]).subject_id == first.id
    assert client.get(f"/subjects/{first.id}/blocks", headers=auth_headers).json() == [block]
    assert client.get(f"/subjects/{second.id}/blocks", headers=auth_headers).json() == []


def test_auth_and_current_role(client, db, subjects, test_user, auth_headers):
    url = f"/subjects/{subjects[0].id}"
    for suffix in ("", "/blocks"):
        assert client.get(url + suffix).status_code == 401
        assert client.get(url + suffix, headers=auth_headers).status_code == 403
    assert client.post(url + "/blocks", json={"name": "B"}).status_code == 401
    assert client.post(url + "/blocks", headers=auth_headers,
                       json={"name": "B"}).status_code == 403
    test_user.role = UserRole.TEACHER
    db.commit()
    assert client.get(url, headers=auth_headers).status_code == 200
    assert client.post(url + "/blocks", headers=auth_headers,
                       json={"name": "B"}).status_code == 201
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.get(url + "/blocks", headers=auth_headers).status_code == 403
    assert client.post(url + "/blocks", headers=auth_headers,
                       json={"name": "C"}).status_code == 403


def test_missing_subject_and_invalid_body(client, db, subjects, test_user, auth_headers):
    test_user.role = UserRole.TEACHER
    db.commit()
    missing = max(item.id for item in subjects) + 100
    assert client.get(f"/subjects/{missing}", headers=auth_headers).status_code == 404
    assert client.get(f"/subjects/{missing}/blocks", headers=auth_headers).status_code == 404
    assert client.post(f"/subjects/{missing}/blocks", headers=auth_headers,
                       json={"name": "A"}).status_code == 404
    url = f"/subjects/{subjects[0].id}/blocks"
    for body in ({}, {"name": "  "}, {"name": "x" * 256},
                 {"name": "A", "subject_id": subjects[1].id},
                 {"name": "A", "role": "admin"}, {"name": "A", "description": 12}):
        assert client.post(url, headers=auth_headers, json=body).status_code == 422
    assert db.scalar(select(func.count()).select_from(ContentBlock)) == 0
    assert client.post(url, headers=auth_headers,
                       json={"name": " " + "x" * 255 + " "}).status_code == 201


def test_order_pagination_and_isolation(client, db, subjects, test_user, auth_headers):
    first, second = subjects
    db.add_all([ContentBlock(subject_id=first.id, name=name) for name in ("Z", "A", "B")])
    db.add(ContentBlock(subject_id=second.id, name="Otro"))
    test_user.role = UserRole.ADMIN
    db.commit()
    url = f"/subjects/{first.id}/blocks"
    all_blocks = client.get(url, headers=auth_headers).json()
    assert [item["name"] for item in all_blocks] == ["Z", "A", "B"]
    assert [item["id"] for item in all_blocks] == sorted(item["id"] for item in all_blocks)
    assert client.get(url + "?skip=1&limit=1", headers=auth_headers).json() == [all_blocks[1]]
    assert client.get(url + "?skip=3&limit=1", headers=auth_headers).json() == []
    assert [item["name"] for item in client.get(
        f"/subjects/{second.id}/blocks", headers=auth_headers).json()] == ["Otro"]
    for query in ("skip=-1", "limit=0", "limit=101"):
        assert client.get(url + "?" + query, headers=auth_headers).status_code == 422
