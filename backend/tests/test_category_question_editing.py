from copy import deepcopy

import pytest
from sqlalchemy import select

from app.models import AnswerLog, Category, ContentBlock, GameSession, Question, Subject, Topic, UserRole


@pytest.fixture
def editable_bank(db, topic):
    subject = Subject(name="Edit subject")
    db.add(subject)
    db.flush()
    blocks = [ContentBlock(name=name, subject_id=subject.id) for name in ("First", "Second")]
    db.add_all(blocks)
    db.flush()
    categories = [Category(name="Own", block_id=blocks[0].id), Category(name="Other", block_id=blocks[1].id)]
    db.add_all(categories)
    db.flush()
    questions = []
    for mode in ("TRIVIAL", "PASAPALABRA"):
        data = body(topic.id, mode)
        questions.append(Question(**data, category_id=categories[0].id,
                                  correct_answer="Original B" if mode == "TRIVIAL" else "Luna"))
    foreign = Question(**body(topic.id), category_id=categories[1].id, correct_answer="Original B")
    other_topic = Topic(name="Changed topic")
    db.add_all(questions + [foreign, other_topic])
    db.commit()
    base = f"/subjects/{subject.id}/blocks/{blocks[0].id}/categories/{categories[0].id}/questions"
    return base, questions, foreign, other_topic, categories, blocks


def body(topic_id, mode="TRIVIAL"):
    data = {"topic_id": topic_id, "text": "Original question", "question_type": mode, "difficulty": 2}
    data.update({"options": ["Original A", "Original B", "Original C", "Original D"], "correct_option_index": 1}
                if mode == "TRIVIAL" else {"letter": "L", "exact_word": "Luna", "accepted_answers": ["Satelite"]})
    return data


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
def test_edit_permissions_and_persistence(client, db, test_user, auth_headers, topic, editable_bank, role, mode):
    base, questions, _, other_topic, _, _ = editable_bank
    question = questions[mode == "PASAPALABRA"]
    path = f"{base}/{question.id}"
    data = body(other_topic.id, mode) | {"text": "Updated question", "difficulty": None}
    assert client.put(path, json=data).status_code == 401
    assert client.put(path, json=data, headers=auth_headers).status_code == 403
    test_user.role = role
    db.commit()
    edited = client.put(path, json=data, headers=auth_headers)
    assert edited.status_code == 200, edited.text
    saved = edited.json()
    db.expire_all()
    assert saved["id"] == question.id and saved["category_id"] == question.category_id
    assert saved["question_type"] == mode
    assert saved["topic_id"] == other_topic.id and saved["topic"]["name"] == other_topic.name
    assert question.text == "Updated question" and question.difficulty is None
    assert any(item == saved for item in client.get(base, headers=auth_headers).json())
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.put(path, json=data, headers=auth_headers).status_code == 403


def test_hierarchy_and_category_isolation(client, db, test_user, auth_headers, topic, editable_bank):
    base, questions, foreign, _, categories, blocks = editable_bank
    test_user.role = UserRole.TEACHER
    db.commit()
    data = body(topic.id)
    before = questions[0].text
    path = f"{base}/{questions[0].id}"
    for position in (2, 4, 6, 8):
        parts = path.split("/")
        parts[position] = "99999"
        assert client.put("/".join(parts), json=data, headers=auth_headers).status_code == 404
    assert client.put(f"{base}/{foreign.id}", json=data, headers=auth_headers).status_code == 404
    for position, identifier in ((4, blocks[1].id), (6, categories[1].id)):
        parts = path.split("/")
        parts[position] = str(identifier)
        assert client.put("/".join(parts), json=data, headers=auth_headers).status_code == 404
    other_subject = Subject(name="Unrelated subject")
    db.add(other_subject)
    db.commit()
    parts = path.split("/")
    parts[2] = str(other_subject.id)
    assert client.put("/".join(parts), json=data, headers=auth_headers).status_code == 404
    assert questions[0].text == before
    assert foreign.text == "Original question"


@pytest.mark.parametrize("mode,changes", [
    ("TRIVIAL", {"text": " "}), ("TRIVIAL", {"options": ["A"]}),
    ("TRIVIAL", {"options": [" ", "B", "C", "D"]}), ("TRIVIAL", {"correct_option_index": 4}),
    ("TRIVIAL", {"letter": "L"}), ("TRIVIAL", {"exact_word": "Luna"}),
    ("TRIVIAL", {"accepted_answers": ["A"]}),
    ("PASAPALABRA", {"letter": "1"}), ("PASAPALABRA", {"exact_word": "Mesa"}),
    ("PASAPALABRA", {"accepted_answers": [" "]}),
    ("PASAPALABRA", {"accepted_answers": ["x"] * 31}),
    ("PASAPALABRA", {"accepted_answers": ["x" * 256]}),
    ("PASAPALABRA", {"correct_option_index": 1}),
] + [(mode, {"difficulty": difficulty}) for mode in ("TRIVIAL", "PASAPALABRA") for difficulty in (0, 5, True, 2.0, "2")])
def test_invalid_edits_never_persist(client, db, test_user, auth_headers, topic, editable_bank, mode, changes):
    base, questions, *_ = editable_bank
    question = questions[mode == "PASAPALABRA"]
    test_user.role = UserRole.TEACHER
    db.commit()
    result = client.put(f"{base}/{question.id}", json=body(topic.id, mode) | changes, headers=auth_headers)
    assert result.status_code == 422, result.text
    db.refresh(question)
    assert question.text == "Original question" and question.difficulty == 2


def test_fixed_identity_and_topic(client, db, test_user, auth_headers, topic, editable_bank):
    base, questions, *_ = editable_bank
    test_user.role = UserRole.ADMIN
    db.commit()
    path = f"{base}/{questions[0].id}"
    for field in ("category_id", "id", "block_id", "subject_id"):
        assert client.put(path, json=body(topic.id) | {field: 1}, headers=auth_headers).status_code == 422
    assert client.put(path, json=body(topic.id, "PASAPALABRA"), headers=auth_headers).status_code == 422
    assert client.put(path, json=body(99999), headers=auth_headers).status_code == 404
    missing = body(topic.id)
    del missing["question_type"]
    assert client.put(path, json=missing, headers=auth_headers).status_code == 422


@pytest.mark.parametrize("mode", ["TRIVIAL", "PASAPALABRA"])
def test_real_edit_keeps_old_session_and_updates_new_games(client, db, test_user, auth_headers, topic, editable_bank, mode):
    base, questions, _, other_topic, categories, _ = editable_bank
    question = questions[mode == "PASAPALABRA"]
    test_user.role = UserRole.TEACHER
    db.commit()
    start = client.post(f"/game/start/{topic.id}", params={"mode": mode, "category_id": categories[0].id}, headers=auth_headers).json()
    session = db.get(GameSession, start["session_id"])
    snapshot = deepcopy(session.question_snapshot)
    data = body(other_topic.id, mode) | {"text": "Edited through API", "difficulty": 4}
    data.update({"options": ["New A", "New B", "New C", "New D"], "correct_option_index": 0}
                if mode == "TRIVIAL" else {"letter": "M", "exact_word": "Mesa", "accepted_answers": ["Mueble", " mueble "]})
    edited = client.put(f"{base}/{question.id}", json=data, headers=auth_headers)
    assert edited.status_code == 200, edited.text
    assert edited.json()["accepted_answers"] == (["Mueble"] if mode == "PASAPALABRA" else None)
    db.refresh(question)
    assert question.correct_answer == ("New A" if mode == "TRIVIAL" else "Mesa")
    db.refresh(session)
    assert session.question_snapshot == snapshot
    answer = {"question_id": question.id, **({"selected_index": 1} if mode == "TRIVIAL" else {"text_answer": "Satelite"})}
    result = client.post(f"/game/submit/{session.id}", json={"answers": [answer]}, headers=auth_headers)
    assert result.status_code == 200 and result.json()["score"] == 1
    saved = client.get(f"/game/history/{session.id}", headers=auth_headers).json()
    assert saved["answer_logs"][0]["question_text"] == "Original question"
    assert saved["content_context"] == start["content_context"]
    new = client.post(f"/game/start/{other_topic.id}", params={"mode": mode, "difficulty": 4, "category_id": categories[0].id}, headers=auth_headers).json()
    assert new["questions"][0]["text"] == "Edited through API"
    assert new["questions"][0]["options"] == edited.json()["options"]
    new_answer = {"question_id": question.id, **({"selected_index": 0} if mode == "TRIVIAL" else {"text_answer": "Mueble"})}
    assert client.post(f"/game/submit/{new['session_id']}", json={"answers": [new_answer]}, headers=auth_headers).json()["score"] == 1
    assert client.get(f"/game/history/{session.id}", headers=auth_headers).json() == saved
    assert len(list(db.scalars(select(AnswerLog)))) == 2
