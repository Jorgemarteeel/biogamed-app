from copy import deepcopy

import pytest

from app.models import GameSession, Subject, UserRole
from test_category_question_editing import body, editable_bank


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
def test_permissions_hierarchy_and_explicit_state(client, db, test_user, auth_headers, editable_bank, role):
    base, questions, foreign, _, categories, blocks = editable_bank
    path = f"{base}/{questions[0].id}/state"
    assert client.put(path, json={"is_active": False}).status_code == 401
    assert client.put(path, json={"is_active": False}, headers=auth_headers).status_code == 403
    test_user.role = role
    db.commit()
    for position in (2, 4, 6, 8):
        parts = path.split("/")
        parts[position] = "99999"
        assert client.put("/".join(parts), json={"is_active": False}, headers=auth_headers).status_code == 404
    subject = Subject(name="Unrelated")
    db.add(subject)
    db.commit()
    for position, value in ((2, subject.id), (4, blocks[1].id), (6, categories[1].id), (8, foreign.id)):
        parts = path.split("/")
        parts[position] = str(value)
        assert client.put("/".join(parts), json={"is_active": False}, headers=auth_headers).status_code == 404
    for invalid in ({}, {"is_active": None}, {"is_active": "false"}, {"is_active": 0}, {"is_active": False, "text": "X"}):
        assert client.put(path, json=invalid, headers=auth_headers).status_code == 422
    for active in (False, False, True, True):
        result = client.put(path, json={"is_active": active}, headers=auth_headers)
        assert result.status_code == 200, result.text
        assert result.json()["is_active"] is active
        db.refresh(questions[0])
        assert questions[0].is_active is active
        assert foreign.is_active
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.put(path, json={"is_active": False}, headers=auth_headers).status_code == 403
    assert client.get(base, headers=auth_headers).status_code == 403


@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
@pytest.mark.parametrize("difficulty", [None, 2])
def test_eligibility_snapshot_correction_history_and_edit(client, db, test_user, auth_headers, topic, editable_bank, mode, difficulty):
    base, questions, _, _, categories, _ = editable_bank
    question = questions[mode == "PASAPALABRA"]
    question.difficulty = difficulty
    test_user.role = UserRole.TEACHER
    db.commit()
    params = {"mode": mode, "category_id": categories[0].id}
    params.update({"difficulty": difficulty} if difficulty else {"difficulty_unknown": True})
    start = client.post(f"/game/start/{topic.id}", params=params, headers=auth_headers).json()
    session = db.get(GameSession, start["session_id"])
    snapshot = deepcopy(session.question_snapshot)
    before_history = client.get(f"/game/history/{session.id}", headers=auth_headers).json()
    path = f"{base}/{question.id}/state"
    assert client.put(path, json={"is_active": False}, headers=auth_headers).json()["is_active"] is False
    db.refresh(session)
    assert session.question_snapshot == snapshot
    assert client.get(f"/game/history/{session.id}", headers=auth_headers).json() == before_history
    for filters in (params, {"mode": mode, "category_id": categories[0].id}):
        availability = client.get(f"/game/availability/{topic.id}", params=filters, headers=auth_headers)
        assert availability.json()["total_questions"] == 0
        assert client.post(f"/game/start/{topic.id}", params=filters, headers=auth_headers).status_code == 409
    # Unscoped starts can still use a different category, but never the retired ID.
    unscoped = client.post(f"/game/start/{topic.id}", params={"mode": mode}, headers=auth_headers)
    if mode == "TRIVIAL":
        assert question.id not in [q["id"] for q in unscoped.json()["questions"]]
    else:
        assert unscoped.status_code == 409
        assert topic.id not in [t["id"] for t in client.get("/topics/", params={"mode": mode}).json()]
    edited = client.put(f"{base}/{question.id}", json=body(topic.id, mode) | {"text": "Edited retired", "difficulty": difficulty}, headers=auth_headers)
    assert edited.status_code == 200 and edited.json()["is_active"] is False
    answer = {"question_id": question.id, **({"selected_index": 1} if mode == "TRIVIAL" else {"text_answer": "Satelite"})}
    result = client.post(f"/game/submit/{session.id}", json={"answers": [answer]}, headers=auth_headers)
    assert result.status_code == 200 and result.json()["score"] == 1
    history = client.get(f"/game/history/{session.id}", headers=auth_headers).json()
    assert history["answer_logs"][0]["question_text"] == "Original question"
    assert history["content_context"] == start["content_context"]
    assert client.put(path, json={"is_active": True}, headers=auth_headers).json()["is_active"] is True
    assert client.get(f"/game/availability/{topic.id}", params=params, headers=auth_headers).json()["total_questions"] == 1
    assert client.get(f"/game/availability/{topic.id}", params={"mode": mode, "category_id": categories[0].id, "difficulty": 4}, headers=auth_headers).json()["total_questions"] == 0
    assert topic.id in [t["id"] for t in client.get("/topics/", params={"mode": mode}).json()]
    new = client.post(f"/game/start/{topic.id}", params=params, headers=auth_headers).json()
    assert new["questions"][0]["id"] == question.id
    assert new["questions"][0]["text"] == "Edited retired"
    assert "correct_option_index" not in new["questions"][0]
    assert "exact_word" not in new["questions"][0]
    assert client.get(f"/game/history/{session.id}", headers=auth_headers).json() == history


def test_state_filters_pagination_and_creation(client, db, test_user, auth_headers, topic, editable_bank):
    base, questions, *_ = editable_bank
    test_user.role = UserRole.TEACHER
    db.commit()
    assert all(q.is_active for q in questions)
    client.put(f"{base}/{questions[0].id}/state", json={"is_active": False}, headers=auth_headers)
    def listing(**params):
        return client.get(base, params=params, headers=auth_headers).json()
    assert [q["id"] for q in listing(state="active")] == [questions[1].id]
    assert [q["id"] for q in listing(state="retired", mode="TRIVIAL", difficulty=2)] == [questions[0].id]
    assert listing(state="retired", mode="PASAPALABRA") == []
    assert listing(state="retired", difficulty_unknown=True) == []
    assert listing(state="all", skip=1, limit=1)[0]["id"] == questions[1].id
    assert listing(state="retired", skip=1, limit=1) == []
    assert len(listing()) == 2
    assert client.get(base, params={"state": "invalid"}, headers=auth_headers).status_code == 422
    created = client.post(base, json=body(topic.id), headers=auth_headers)
    assert created.status_code == 201 and created.json()["is_active"] is True
    assert client.post(base, json=body(topic.id) | {"is_active": False}, headers=auth_headers).status_code == 422
