from app.models import GameSession, User


def test_progress_requires_authentication(client):
    assert client.get("/game/progress").status_code == 401


def test_progress_empty(client, auth_headers):
    response = client.get("/game/progress", headers=auth_headers)
    assert response.status_code == 200
    zero = {"started": 0, "completed": 0, "unfinished": 0}
    assert response.json() == {**zero, "by_mode": {"TRIVIAL": zero, "PASAPALABRA": zero}}


def test_progress_aggregates_all_user_sessions(client, db, topic, test_user, auth_headers):
    other = User(name="Other", email="progress-other@example.com", hashed_password="unused")
    db.add(other)
    db.flush()
    for index in range(26):
        db.add(GameSession(user_id=test_user.id, topic_id=topic.id,
                           game_mode="TRIVIAL" if index < 23 else "PASAPALABRA",
                           question_ids=[index + 1], score=0,
                           is_completed=index % 2 == 0))
    db.add(GameSession(user_id=other.id, topic_id=topic.id, game_mode="TRIVIAL",
                       question_ids=[99], score=8, is_completed=True))
    db.commit()

    response = client.get("/game/progress", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "started": 26, "completed": 13, "unfinished": 13,
        "by_mode": {
            "TRIVIAL": {"started": 23, "completed": 12, "unfinished": 11},
            "PASAPALABRA": {"started": 3, "completed": 1, "unfinished": 2},
        },
    }
    for counts in [data, *data["by_mode"].values()]:
        assert counts["started"] == counts["completed"] + counts["unfinished"]
