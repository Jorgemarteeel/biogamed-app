from app.models import Category, GameSession, Question


def bank(db, topic):
    a = Category(name="Linfocito")
    b = Category(name="Macrófago")
    db.add_all([a, b])
    db.flush()
    def trivial(name, category=None, difficulty=None):
        return Question(topic_id=topic.id, text=name, question_type="TRIVIAL",
                        options=["A", "B", "C", "D"], correct_option_index=1,
                        correct_answer="B", category=category, difficulty=difficulty)
    chosen = [trivial(f"Chosen {i}", a, 2) for i in range(12)]
    other = [trivial("Other category", b, 2), trivial("Other level", a, 3),
             trivial("Unknown", a), trivial("Unclassified")]
    word = Question(topic_id=topic.id, text="Starts A", question_type="PASAPALABRA",
                    letter="A", exact_word="Aorta", correct_answer="Aorta")
    db.add_all(chosen + other + [word])
    db.commit()
    return a, b, chosen, other, word


def test_availability_and_filtered_start_preserve_snapshot(db, client, topic,
                                                            auth_headers, test_user):
    a, b, chosen, other, word = bank(db, topic)
    url = f"/game/availability/{topic.id}"
    start = f"/game/start/{topic.id}"
    assert client.get(url).status_code == 401
    availability = client.get(url, headers=auth_headers).json()
    assert availability["total_questions"] == 16
    assert {tuple(item[key] for key in ("category_id", "category_name", "difficulty", "count"))
            for item in availability["combinations"]} == {
        (a.id, "Linfocito", 2, 12), (a.id, "Linfocito", 3, 1),
        (a.id, "Linfocito", None, 1), (b.id, "Macrófago", 2, 1),
        (None, None, None, 1),
    }
    assert not any("text" in item or "answer" in item
                   for item in availability["combinations"])
    params = {"category_id": a.id, "difficulty": 2}
    filtered = client.get(url, params=params, headers=auth_headers).json()
    assert filtered["total_questions"] == 12
    assert filtered["combinations"] == [
        {"category_id": a.id, "category_name": "Linfocito", "difficulty": 2, "count": 12}]
    response = client.post(start, params=params, headers=auth_headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert len(data["questions"]) == 10
    assert len({q["id"] for q in data["questions"]}) == 10
    assert {q["id"] for q in data["questions"]} <= {q.id for q in chosen}
    assert all("correct_option_index" not in q and "correct_answer" not in q
               for q in data["questions"])
    assert "answer" not in str(data["content_context"])
    session = db.get(GameSession, data["session_id"])
    snapshot = session.content_context
    assert snapshot["selection"] == {"category_id": a.id, "category_name": a.name,
                                     "difficulty": 2, "difficulty_unknown": False}
    assert {item["difficulty"] for item in snapshot["questions"]} == {2}
    selected = next(q for q in chosen if q.id == data["questions"][0]["id"])
    selected.category = b
    selected.difficulty = 4
    a.name = "Renamed"
    db.commit()
    history = client.get(f"/game/history/{session.id}", headers=auth_headers).json()
    assert history["content_context"] == snapshot
    assert client.get(url, params={"mode": "PASAPALABRA"},
                      headers=auth_headers).json()["total_questions"] == 1
    assert client.post(start, params={"mode": "PASAPALABRA"},
                       headers=auth_headers).status_code == 201


def test_unknown_empty_invalid_and_unfiltered(db, client, topic, auth_headers):
    a, _, chosen, other, word = bank(db, topic)
    url = f"/game/availability/{topic.id}"
    start = f"/game/start/{topic.id}"
    unknown = {"category_id": a.id, "difficulty_unknown": "true"}
    assert client.get(url, params=unknown, headers=auth_headers).json()["total_questions"] == 1
    response = client.post(start, params=unknown, headers=auth_headers)
    assert response.status_code == 201
    assert [q["id"] for q in response.json()["questions"]] == [other[2].id]
    assert client.post(start, headers=auth_headers).status_code == 201
    assert client.post(start, params={"category_id": a.id, "difficulty": 1},
                       headers=auth_headers).status_code == 409
    for params in ({"difficulty": 0}, {"difficulty": 5}, {"difficulty": "2.5"},
                   {"category_id": 0}, {"difficulty": 2, "difficulty_unknown": "true"}):
        assert client.get(url, params=params, headers=auth_headers).status_code == 422
        assert client.post(start, params=params, headers=auth_headers).status_code == 422
