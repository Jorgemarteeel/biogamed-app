from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import AnswerLog, Category, ContentBlock, GameSession, Question, Subject, UserRole
from app.models.pasapalabra import MatchQuestion
from app.schemas.game import UserAnswer
from app.schemas.pasapalabra import LocalStart
from app.services import game, pasapalabra


@pytest.fixture
def hierarchy(db, topic):
    subject = Subject(name="Original", description="Asignatura")
    db.add(subject); db.flush()
    block = ContentBlock(name="Original", description="Bloque", subject_id=subject.id)
    db.add(block); db.flush()
    category = Category(name="Original", description="Categoría", block_id=block.id)
    db.add(category); db.flush()
    for mode, count in (("TRIVIAL", 1), ("PASAPALABRA", 40)):
        for i in range(count):
            db.add(Question(topic_id=topic.id, category_id=category.id, text=f"Histórica {i}",
                            question_type=mode, correct_answer="A", difficulty=2,
                            options=["A", "B", "C", "D"] if mode == "TRIVIAL" else None,
                            correct_option_index=0 if mode == "TRIVIAL" else None,
                            letter="A" if mode == "PASAPALABRA" else None,
                            exact_word="A" if mode == "PASAPALABRA" else None))
    db.commit()
    return subject, block, category


def urls(hierarchy):
    s, b, c = hierarchy
    return [f"/subjects/{s.id}", f"/subjects/{s.id}/blocks/{b.id}",
            f"/subjects/{s.id}/blocks/{b.id}/categories/{c.id}"]


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
def test_edit_metadata_preserves_relations_and_real_historical_copies(client, db, test_user, auth_headers, hierarchy, role):
    s, b, c = hierarchy
    selection = dict(subject_id=s.id, block_id=b.id, category_id=c.id)
    trivial = game.start_game_session(db, test_user, topic_id=None, **selection)
    game.submit_game_session(db, test_user, trivial.session_id,
                             [UserAnswer(question_id=q.id, selected_index=0) for q in trivial.questions])
    answers = [deepcopy({column.name: getattr(row, column.name) for column in AnswerLog.__table__.columns})
               for row in db.scalars(select(AnswerLog))]
    match = pasapalabra.start_local(db, test_user, LocalStart(**selection, guest_name="Ficticio", operation_id=uuid4()))
    # An old incomplete session has no historical copy: editing must not rebuild it.
    db.add(GameSession(user_id=test_user.id, topic_id=None, question_ids=[], score=0,
                       is_completed=False, question_snapshot=None))
    db.commit()
    sessions = list(db.scalars(select(GameSession)))
    before = [(row.id, deepcopy(row.question_snapshot), deepcopy(row.content_context)) for row in sessions]
    assigned = list(db.scalars(select(MatchQuestion)))
    snapshots = [(row.id, deepcopy(row.snapshot)) for row in assigned]
    questions = [(q.id, q.topic_id, q.category_id, q.is_active, q.text) for q in db.scalars(select(Question))]
    test_user.role = role; db.commit()
    for entity, url in zip(hierarchy, urls(hierarchy)):
        response = client.patch(url, headers=auth_headers, json={"name": "  Actualizado  ", "description": None})
        assert response.status_code == 200, response.text
        assert response.json()["id"] == entity.id
        db.refresh(entity)
        assert entity.name == "Actualizado" and entity.description is None
    # Existing rules allow duplicate labels; identity is the ID, not the name.
    assert c.block_id == b.id and b.subject_id == s.id
    assert questions == [(q.id, q.topic_id, q.category_id, q.is_active, q.text) for q in db.scalars(select(Question))]
    db.expire_all()
    assert before == [(row.id, row.question_snapshot, row.content_context) for row in db.scalars(select(GameSession))]
    assert snapshots == [(row.id, row.snapshot) for row in db.scalars(select(MatchQuestion))]
    assert answers == [{column.name: getattr(row, column.name) for column in AnswerLog.__table__.columns}
                       for row in db.scalars(select(AnswerLog))]
    assert pasapalabra.read_state(db, test_user, match['id'])['academic']['subject_name'] == 'Original'
    assert game.get_game_history_detail(db, test_user, trivial.session_id).content_context['academic']['category_name'] == 'Original'


def test_edit_auth_validation_and_path_isolation(client, db, test_user, auth_headers, hierarchy):
    for url in urls(hierarchy):
        assert client.patch(url, json={"name": "No"}).status_code == 401
        assert client.patch(url, headers=auth_headers, json={"name": "No"}).status_code == 403
    test_user.role = UserRole.TEACHER; db.commit()
    for url in urls(hierarchy):
        for payload in ({}, {"name": "  "}, {"name": "x" * 256}, {"name": "A", "description": 3},
                        {"name": "A", "block_id": 9}, {"name": "A", "is_active": False}, {"name": "A", "id": 8}):
            assert client.patch(url, headers=auth_headers, json=payload).status_code == 422
        assert client.patch(url, headers=auth_headers, json={"name": " " + "x" * 255 + " ", "description": "Texto"}).status_code == 200
    other = Subject(name="Otro"); db.add(other); db.commit()
    _, b, c = hierarchy
    for url in (f"/subjects/{other.id}/blocks/{b.id}", f"/subjects/{other.id}/blocks/{b.id}/categories/{c.id}",
                f"/subjects/{other.id}/blocks/99999/categories/{c.id}", "/subjects/99999"):
        assert client.patch(url, headers=auth_headers, json={"name": "No"}).status_code == 404
    # A token obtained before losing the staff role must not authorize updates.
    test_user.role = UserRole.STUDENT; db.commit()
    assert client.patch(urls(hierarchy)[0], headers=auth_headers, json={"name": "No"}).status_code == 403


def test_duplicate_labels_keep_existing_policy(client, db, test_user, auth_headers, hierarchy):
    s, b, c = hierarchy
    db.add_all([Subject(name="Repeated"), ContentBlock(name="Repeated", subject_id=s.id),
                Category(name="Repeated", block_id=b.id)])
    test_user.role = UserRole.TEACHER
    db.commit()
    for url in urls(hierarchy):
        response = client.patch(url, headers=auth_headers, json={"name": "Repeated", "description": "Same label, different ID"})
        assert response.status_code == 200, response.text
