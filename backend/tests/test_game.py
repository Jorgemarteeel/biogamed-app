import pytest

from app.models import GameSession, Question


@pytest.mark.parametrize(
    "selected_index, expected_score",
    [(2, 1), (0, 0)],
    ids=["correct-answer", "incorrect-answer"],
)
def test_game_engine_trivial(client, db, topic, auth_headers, selected_index, expected_score):
    question = Question(
        text="Which organ pumps blood?",
        topic_id=topic.id,
        question_type="TRIVIAL",
        options=["Lung", "Liver", "Heart", "Kidney"],
        correct_option_index=2,
        correct_answer="Heart",
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    start = client.post(f"/game/start/{topic.id}", headers=auth_headers)
    assert start.status_code == 201, start.text
    game = start.json()
    assert [item["id"] for item in game["questions"]] == [question.id]
    assert "correct_option_index" not in game["questions"][0]

    response = client.post(
        f"/game/submit/{game['session_id']}",
        headers=auth_headers,
        json={"answers": [{"question_id": question.id, "selected_index": selected_index}]},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["score"] == expected_score
    assert result["total_questions"] == 1
    assert len(result["corrections"]) == 1
    correction = result["corrections"][0]
    assert correction["question_id"] == question.id
    assert correction["is_correct"] is bool(expected_score)
    assert correction["correct_option_index"] == 2
    db.expire_all()
    session = db.get(GameSession, game["session_id"])
    assert session.is_completed is True
    assert session.score == expected_score


@pytest.mark.parametrize("text_answer", ["Aorta", "  aORTA  ", "\tAORTA\n"])
def test_game_engine_pasapalabra(client, db, topic, auth_headers, text_answer):
    question = Question(
        text="Starts with A: the main artery leaving the heart.",
        topic_id=topic.id,
        question_type="PASAPALABRA",
        letter="A",
        exact_word="Aorta",
        correct_answer="Aorta",
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    start = client.post(
        f"/game/start/{topic.id}",
        params={"mode": "PASAPALABRA"},
        headers=auth_headers,
    )
    assert start.status_code == 201, start.text
    game = start.json()
    assert [item["id"] for item in game["questions"]] == [question.id]
    assert game["questions"][0]["letter"] == "A"
    assert "exact_word" not in game["questions"][0]

    response = client.post(
        f"/game/submit/{game['session_id']}",
        headers=auth_headers,
        json={"answers": [{"question_id": question.id, "text_answer": text_answer}]},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["score"] == 1
    assert result["total_questions"] == 1
    assert len(result["corrections"]) == 1
    correction = result["corrections"][0]
    assert correction["question_id"] == question.id
    assert correction["is_correct"] is True
    assert correction["exact_word"] == "Aorta"
    db.expire_all()
    session = db.get(GameSession, game["session_id"])
    assert session.is_completed is True
    assert session.score == 1
