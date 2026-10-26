import pytest

from app.models import Question, UserRole
from app.utils.answers import is_accepted_answer, normalize_answer


@pytest.mark.parametrize("value, expected", [
    ("  CÉLULA  ", "celula"), ("ce\u0301lula", "celula"),
    ("MÉDULA   ÓSEA", "medula osea"), ("PINGÜINO", "pinguino"),
    ("SEÑAL", "señal"), ("sen\u0303al", "señal"),
])
def test_normalization(value, expected):
    assert normalize_answer(value) == expected


def test_no_fuzzy_matches_or_accidental_enye_equivalence():
    assert not is_accepted_answer("ano", "año", [])
    assert not is_accepted_answer("arteria", "aorta", [])
    assert not is_accepted_answer(" ", "célula", [" "])
    assert not is_accepted_answer("globulo blanco", "leucocito", [])
    assert is_accepted_answer(" GLÓBULO  BLANCO ", "leucocito", ["glóbulo blanco"])


@pytest.mark.parametrize("answer, correct", [
    ("leucocito", True), ("  GLÓBULO   BLANCO  ", True),
    ("glo\u0301bulo blanco", True), ("glóbulo rojo", False),
])
def test_alias_management_scoring_history_and_privacy(
    client, db, topic, test_user, auth_headers, answer, correct,
):
    test_user.role = UserRole.TEACHER
    db.commit()
    created = client.post("/questions/", headers=auth_headers, json={
        "topic_id": topic.id, "text": "Empieza por la letra L: Célula de defensa.",
        "question_type": "PASAPALABRA", "letter": "L", "exact_word": "leucocito",
        "accepted_answers": [],
    })
    assert created.status_code == 201, created.text
    question_id = created.json()["id"]
    url = f"/questions/{question_id}/accepted-answers"
    payload = {"accepted_answers": ["glóbulo blanco", " GLOBULO BLANCO "]}
    assert client.patch(url, json=payload).status_code == 401
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.patch(url, json=payload, headers=auth_headers).status_code == 403
    test_user.role = UserRole.TEACHER
    db.commit()
    updated = client.patch(url, json=payload, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["accepted_answers"] == ["glóbulo blanco"]
    assert client.patch(url, json={"accepted_answers": [" "]}, headers=auth_headers).status_code == 422
    assert client.patch(url, json={}, headers=auth_headers).status_code == 422
    test_user.role = UserRole.STUDENT
    db.commit()
    start = client.post(f"/game/start/{topic.id}?mode=PASAPALABRA", headers=auth_headers)
    assert start.status_code == 201
    assert "accepted_answers" not in start.json()["questions"][0]
    session_id = start.json()["session_id"]
    result = client.post(f"/game/submit/{session_id}", headers=auth_headers, json={
        "answers": [{"question_id": question_id, "text_answer": answer}],
    })
    assert result.status_code == 200, result.text
    assert result.json()["score"] == int(correct)
    question = db.get(Question, question_id)
    question.accepted_answers = []
    db.commit()
    history = client.get(f"/game/history/{session_id}", headers=auth_headers).json()
    assert history["answer_logs"][0]["accepted_answers"] == ["glóbulo blanco"]
    assert history["answer_logs"][0]["text_answer"] == answer


def test_accented_canonical_word_creation_and_scoring(client, db, topic, test_user, auth_headers):
    test_user.role = UserRole.ADMIN
    db.commit()
    result = client.post("/questions/", headers=auth_headers, json={
        "topic_id": topic.id, "text": "Empieza por A: órgano.",
        "question_type": "PASAPALABRA", "letter": "A", "exact_word": "Árbol",
        "accepted_answers": ["árbol"],
    })
    assert result.status_code == 201, result.text
    game = client.post(f"/game/start/{topic.id}?mode=PASAPALABRA", headers=auth_headers).json()
    response = client.post(f"/game/submit/{game['session_id']}", headers=auth_headers, json={
        "answers": [{"question_id": result.json()["id"], "text_answer": "arbol"}],
    })
    assert response.json()["score"] == 1
