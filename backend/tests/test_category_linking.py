from app.models import Category, ContentBlock, GameSession, Question, Subject, UserRole


def prepare(db, topic, user):
    subject = Subject(name="Asignatura")
    db.add(subject)
    db.flush()
    first = ContentBlock(subject_id=subject.id, name="A")
    second = ContentBlock(subject_id=subject.id, name="B")
    orphan = Category(name="Origen", description="Conservar")
    db.add_all([first, second, orphan])
    db.flush()
    question = Question(topic_id=topic.id, category_id=orphan.id,
                        difficulty=2, text="Pregunta", correct_answer="Sí")
    db.add(question)
    db.flush()
    game = GameSession(user_id=user.id, topic_id=topic.id, question_ids=[question.id],
                       content_context={"category_id": orphan.id, "difficulty": 2})
    db.add(game)
    db.commit()
    return subject, first, second, orphan, question, game


def test_staff_list_and_link_preserve_existing_data(client, db, topic, test_user, auth_headers):
    subject, first, second, orphan, question, game = prepare(db, topic, test_user)
    url = "/subjects/categories/unassigned"
    target = f"/subjects/{subject.id}/blocks/{first.id}/categories/{orphan.id}"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth_headers).status_code == 403
    assert client.put(target, headers=auth_headers, json={}).status_code == 403
    test_user.role = UserRole.TEACHER
    db.commit()
    assert [item["id"] for item in client.get(url, headers=auth_headers).json()] == [orphan.id]
    assert client.put(target, headers=auth_headers, json={"block_id": second.id}).status_code == 422
    response = client.put(target, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    assert response.json() == {"id": orphan.id, "block_id": first.id,
                               "name": "Origen", "description": "Conservar"}
    assert client.put(target, headers=auth_headers, json={}).status_code == 200
    assert client.get(url, headers=auth_headers).json() == []
    assert [item["id"] for item in client.get(
        f"/subjects/{subject.id}/blocks/{first.id}/categories", headers=auth_headers).json()] == [orphan.id]
    assert client.get(f"/subjects/{subject.id}/blocks/{second.id}/categories",
                      headers=auth_headers).json() == []
    db.refresh(question)
    db.refresh(game)
    assert question.category_id == orphan.id and question.topic_id == topic.id
    assert question.difficulty == 2 and game.question_ids == [question.id]
    assert game.content_context == {"category_id": orphan.id, "difficulty": 2}


def test_references_conflict_pagination_and_role(client, db, topic, test_user, auth_headers):
    subject, first, second, orphan, _, _ = prepare(db, topic, test_user)
    db.add_all([Category(name="Duplicado"), Category(name="Duplicado")])
    test_user.role = UserRole.ADMIN
    db.commit()
    url = "/subjects/categories/unassigned"
    items = client.get(url, headers=auth_headers).json()
    assert len(items) == 3 and all(item["block_id"] is None for item in items)
    assert client.get(url + "?skip=1&limit=1", headers=auth_headers).json() == [items[1]]
    assert client.get(url + "?limit=101", headers=auth_headers).status_code == 422
    base = f"/subjects/{subject.id}/blocks/{first.id}/categories/"
    assert client.put(base + "99999", headers=auth_headers, json={}).status_code == 404
    assert client.put(f"/subjects/99999/blocks/{first.id}/categories/{orphan.id}",
                      headers=auth_headers, json={}).status_code == 404
    assert client.put(f"/subjects/{subject.id}/blocks/99999/categories/{orphan.id}",
                      headers=auth_headers, json={}).status_code == 404
    assert client.put(base + str(orphan.id), headers=auth_headers, json={}).status_code == 200
    assert client.put(f"/subjects/{subject.id}/blocks/{second.id}/categories/{orphan.id}",
                      headers=auth_headers, json={}).status_code == 409
    db.refresh(orphan)
    assert orphan.block_id == first.id
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.get(url, headers=auth_headers).status_code == 403
