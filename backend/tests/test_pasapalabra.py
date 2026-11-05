from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, func

from app.models import Category, GameSession, Question, Topic, User, AnswerLog
from app.models.pasapalabra import PasapalabraMatch, MatchQuestion, MatchCommand
from app.services import pasapalabra as engine


@pytest.fixture
def clock(monkeypatch):
    clock = [datetime(2030, 1, 1, tzinfo=timezone.utc)]
    monkeypatch.setattr(engine, "server_now", lambda db: clock[0])
    monkeypatch.setattr(engine.RNG, "choice", lambda values: 1)
    return clock


def bank(db, topic, count=40, **fields):
    rows = [Question(topic_id=topic.id, text=f"Pista privada {i}", question_type="PASAPALABRA",
                     letter="A", exact_word="Árbol", correct_answer="Árbol",
                     accepted_answers=["Roble"], **fields) for i in range(count)]
    db.add_all(rows)
    db.commit()
    return rows


def start(client, headers, topic, **overrides):
    payload = {"operation_id": str(uuid4()), "topic_id": topic.id, "guest_name": "Invitada", **overrides}
    response = client.post("/pasapalabra/local/start", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json(), payload


def command(client, headers, state, kind="answer", text="ARBOL", **overrides):
    active = state["active_question"]
    payload = {"operation_id": str(uuid4()), "expected_version": state["version"],
               "participant": active["participant"], "number": active["number"]}
    if kind == "answer":
        payload["text_answer"] = text
    if kind == "abandon":
        payload.pop("number")
    payload.update(overrides)
    response = client.post(f"/pasapalabra/matches/{state['id']}/{kind}", json=payload, headers=headers)
    return response, payload


def apply(client, headers, state, **kwargs):
    response, _ = command(client, headers, state, **kwargs)
    assert response.status_code == 200, response.text
    return response.json()["state"]


def test_selection_filters_snapshots_and_insufficiency(db, client, topic, auth_headers, clock):
    category = Category(name="Categoría ficticia")
    db.add(category)
    db.commit()
    chosen = bank(db, topic, category_id=category.id, difficulty=2)
    bank(db, topic, 5, difficulty=3)
    bank(db, topic, 5, category_id=category.id, difficulty=2, is_active=False)
    other = Topic(name="Otra temática")
    db.add(other)
    db.commit()
    bank(db, other, 5, category_id=category.id, difficulty=2)
    filters = {"topic_id": topic.id, "category_id": category.id, "difficulty": 2}
    available = client.post("/pasapalabra/preparations", json=filters, headers=auth_headers).json()
    assert available["available"] == available["required"] == 40
    state, _ = start(client, auth_headers, topic, category_id=category.id, difficulty=2)
    slots = list(db.scalars(select(MatchQuestion)))
    assert len(slots) == len({s.question_id for s in slots}) == 40
    assert {s.question_id for s in slots} == {q.id for q in chosen}
    assert [len(p["slots"]) for p in state["participants"]] == [20, 20]
    chosen[0].is_active = False
    db.commit()
    failed = client.post("/pasapalabra/local/start", headers=auth_headers,
                         json={**filters, "operation_id": str(uuid4()), "guest_name": "Invitado"})
    assert failed.status_code == 409
    assert failed.json()["detail"]["available"] == 39
    assert db.scalar(select(func.count()).select_from(PasapalabraMatch)) == 1
    assert db.scalar(select(func.count()).select_from(GameSession)) == 1


def test_unknown_difficulty_and_validation(db, client, topic, auth_headers, clock):
    bank(db, topic)
    bank(db, topic, 5, difficulty=2)
    state, _ = start(client, auth_headers, topic, difficulty_unknown=True)
    assert all(s.snapshot["classification"]["difficulty"] is None for s in db.scalars(select(MatchQuestion)))
    for payload in [{"difficulty": 2, "difficulty_unknown": True}, {"difficulty": 5},
                    {"category_id": 0}, {"questions_per_player": 10}]:
        response = client.post("/pasapalabra/preparations", headers=auth_headers,
                               json={"topic_id": topic.id, **payload})
        assert response.status_code == 422


def test_circular_pass_correct_wrong_and_repeated_pass(db, client, topic, auth_headers, clock):
    bank(db, topic)
    state, _ = start(client, auth_headers, topic)
    assert state["active_participant"] == 1
    clock[0] += timedelta(seconds=10)
    state = apply(client, auth_headers, state, kind="pass")
    assert state["active_participant"] == 2
    assert state["participants"][0]["remaining_ms"] == 590000
    assert state["participants"][0]["wrong"] == 0
    state = apply(client, auth_headers, state, text="incorrecta")
    assert state["active_participant"] == 1
    assert state["participants"][1]["wrong"] == 1
    for _ in range(19):
        state = apply(client, auth_headers, state, text="  rObLe  ")
    assert state["active_question"]["number"] == 1
    state = apply(client, auth_headers, state, kind="pass")
    state = apply(client, auth_headers, state, kind="pass")
    assert state["active_question"]["number"] == 1
    state = apply(client, auth_headers, state)
    assert state["participants"][0]["finish_reason"] == "RESOLVED"
    assert state["active_participant"] == 2
    # Rival finished: mistakes and passes retain the only playable participant.
    state = apply(client, auth_headers, state, kind="pass")
    assert state["active_participant"] == 2
    while state["status"] == "RUNNING":
        state = apply(client, auth_headers, state, text="incorrecta")
    assert state["outcome"] == "NORMAL" and state["winner_position"] == 1
    assert [p["pending"] for p in state["participants"]] == [0, 0]


def test_last_correct_tie_and_normal_history(db, client, topic, auth_headers, clock):
    bank(db, topic)
    state, _ = start(client, auth_headers, topic)
    for _ in range(40):
        state = apply(client, auth_headers, state)
    assert state["status"] == "FINISHED" and state["winner_position"] is None
    assert state["active_question"] is None
    assert [p["correct"] for p in state["participants"]] == [20, 20]
    result = client.get(f"/pasapalabra/matches/{state['id']}/result", headers=auth_headers)
    assert result.json()["outcome"] == "NORMAL"
    history = client.get(f"/game/history/{state['personal_session_id']}", headers=auth_headers).json()
    assert history["is_completed"] and len(history["answer_logs"]) == 20
    assert history["wrong_count"] == history["pending_count"] == 0
    assert client.get("/game/progress", headers=auth_headers).json()["completed"] == 1


@pytest.mark.parametrize("elapsed", [599999, 600000, 1200000, 1500000])
def test_real_deadlines_recovery_and_rejected_action_persists(db, client, topic, auth_headers, clock, elapsed):
    bank(db, topic)
    state, _ = start(client, auth_headers, topic)
    clock[0] += timedelta(milliseconds=elapsed)
    response, _ = command(client, auth_headers, state)
    if elapsed < 600000:
        assert response.status_code == 200
        assert response.json()["state"]["participants"][0]["remaining_ms"] == 1
    else:
        assert response.status_code == 409
    # New ORM state, as after a process restart; no browser timer participates.
    db.expire_all()
    recovered = client.get(f"/pasapalabra/matches/{state['id']}", headers=auth_headers).json()
    if elapsed >= 600000:
        assert recovered["participants"][0]["finish_reason"] == "TIMEOUT"
        assert recovered["participants"][0]["correct"] == 0
        assert recovered["participants"][0]["pending"] == 20
        assert recovered["participants"][0]["wrong"] == 0
    if elapsed >= 1200000:
        assert recovered["status"] == "FINISHED"
        assert recovered["winner_position"] is None
        assert recovered["finished_at"].startswith("2030-01-01T00:20:00")
    elif elapsed >= 600000:
        assert recovered["active_participant"] == 2


def test_history_itself_reconciles_expired_matches(db, client, topic, auth_headers, clock):
    bank(db, topic)
    state, _ = start(client, auth_headers, topic)
    clock[0] += timedelta(minutes=30)
    progress = client.get("/game/progress", headers=auth_headers).json()
    assert progress["completed"] == 1 and progress["unfinished"] == 0
    history = client.get("/game/history", headers=auth_headers).json()
    assert history[0]["pending_count"] == 20 and history[0]["wrong_count"] == 0


@pytest.mark.parametrize("abandoning", [1, 2])
def test_abandonment_forfeit_preserves_results_excludes_marks(db, client, topic, auth_headers, clock, abandoning):
    category = Category(name="Ficticia")
    db.add(category)
    db.commit()
    bank(db, topic, category_id=category.id, difficulty=2)
    state, _ = start(client, auth_headers, topic)
    state = apply(client, auth_headers, state)
    state = apply(client, auth_headers, state, kind="abandon", participant=abandoning)
    assert state["outcome"] == "ABANDONMENT" and state["winner_position"] == 3 - abandoning
    assert state["participants"][0]["correct"] == 1
    history = client.get(f"/game/history/{state['personal_session_id']}", headers=auth_headers).json()
    assert not history["is_completed"] and history["match_status"] == "FINISHED"
    assert history["completion_reason"] == "ABANDONMENT" and len(history["answer_logs"]) == 1
    assert history["pending_count"] == 19
    assert client.get("/game/progress", headers=auth_headers).json()["best_marks"] == []


def test_retry_versions_authorization_and_legacy_submit(db, client, topic, auth_headers, test_user, clock):
    bank(db, topic)
    state, payload = start(client, auth_headers, topic)
    again = client.post("/pasapalabra/local/start", headers=auth_headers, json=payload)
    assert again.json()["id"] == state["id"]
    payload["guest_name"] = "Otra"
    assert client.post("/pasapalabra/local/start", headers=auth_headers, json=payload).status_code == 409
    assert command(client, auth_headers, state, participant=2)[0].json()["detail"]["code"] == "OUT_OF_TURN"
    response, payload = command(client, auth_headers, state)
    next_state = response.json()["state"]
    clock[0] += timedelta(seconds=3)
    repeated = client.post(f"/pasapalabra/matches/{state['id']}/answer", headers=auth_headers, json=payload)
    assert repeated.json()["operation"] == response.json()["operation"]
    assert repeated.json()["state"]["version"] == next_state["version"]
    assert repeated.json()["state"]["participants"][0]["correct"] == 1
    assert repeated.json()["state"]["participants"][0]["remaining_ms"] == 597000
    assert db.scalar(select(func.count()).select_from(AnswerLog)) == 1
    assert command(client, auth_headers, state)[0].json()["detail"]["code"] == "STALE_VERSION"
    payload["text_answer"] = "otra"
    assert client.post(f"/pasapalabra/matches/{state['id']}/answer", headers=auth_headers, json=payload).status_code == 409
    legacy = client.post(f"/game/submit/{state['personal_session_id']}", headers=auth_headers,
                         json={"answers": [{"question_id": 1, "text_answer": "ARBOL"}]})
    assert legacy.json()["detail"]["code"] == "SHARED_MATCH_REQUIRES_COMMANDS"
    assert client.get(f"/pasapalabra/matches/{state['id']}").status_code == 401
    stranger = User(name="Otra cuenta", email="stranger@example.test", hashed_password="unused")
    db.add(stranger)
    db.commit()
    from app.dependencies import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: stranger
    try:
        assert client.get(f"/pasapalabra/matches/{state['id']}", headers=auth_headers).status_code == 404
        assert client.get(f"/pasapalabra/matches/{state['id']}/result", headers=auth_headers).status_code == 404
        assert command(client, auth_headers, next_state)[0].status_code == 404
        assert command(client, auth_headers, next_state, kind="pass")[0].status_code == 404
        assert command(client, auth_headers, next_state, kind="abandon")[0].status_code == 404
        assert client.get(f"/game/history/{state['personal_session_id']}", headers=auth_headers).status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user)


def test_private_future_solutions_and_snapshot_survive_bank_edits(db, client, topic, auth_headers, clock):
    bank(db, topic)
    state, _ = start(client, auth_headers, topic)
    assert "Árbol" not in str(state) and "Roble" not in str(state)
    assert "snapshot" not in str(state) and "question_ids" not in str(state)
    assert sum("Pista privada" in str(v) for v in [state["active_question"]]) == 1
    slots = list(db.scalars(select(MatchQuestion)))
    original = [s.snapshot for s in slots]
    for q in db.scalars(select(Question)):
        q.exact_word = "Nueva solución"
        q.accepted_answers = []
        q.text = "Enunciado nuevo"
        q.is_active = False
    db.commit()
    state = apply(client, auth_headers, state, text="roble")
    assert state["participants"][0]["correct"] == 1
    assert len(state["participants"][0]["resolved"]) == 1
    assert state["participants"][0]["resolved"][0]["exact_word"] == "Árbol"
    assert [s.snapshot for s in db.scalars(select(MatchQuestion))] == original
    private_history = client.get(f"/game/history/{state['personal_session_id']}", headers=auth_headers).json()
    assert "question_snapshot" not in private_history and private_history["answer_logs"] == []


def test_shared_best_mark_timeout_partial_and_format(db, client, topic, auth_headers, clock):
    category = Category(name="Ficticia")
    db.add(category)
    db.commit()
    bank(db, topic, category_id=category.id, difficulty=2)
    state, _ = start(client, auth_headers, topic)
    state = apply(client, auth_headers, state)
    clock[0] += timedelta(minutes=25)
    marks = client.get("/game/progress", headers=auth_headers).json()["best_marks"]
    assert len(marks) == 1
    assert marks[0]["total_questions"] == 20 and marks[0]["best_score"] == 1
    assert marks[0]["format_key"] == engine.RULES


def test_guest_can_start_but_never_generates_personal_progress(db, client, topic, auth_headers, clock, monkeypatch):
    bank(db, topic)
    monkeypatch.setattr(engine.RNG, "choice", lambda values: 2)
    state, _ = start(client, auth_headers, topic)
    assert state["active_participant"] == 2
    state = apply(client, auth_headers, state)
    assert state["participants"][1]["correct"] == 1
    assert db.scalar(select(func.count()).select_from(GameSession)) == 1
    assert db.scalar(select(func.count()).select_from(AnswerLog)) == 0
    state = apply(client, auth_headers, state, kind="abandon", participant=1)
    assert state["winner_position"] == 2
    history = client.get("/game/history", headers=auth_headers).json()
    assert len(history) == 1 and history[0]["score"] == 0
    assert history[0]["pending_count"] == 20


def test_partial_rival_clock_is_not_reset_after_timeout(db, client, topic, auth_headers, clock):
    bank(db, topic)
    state, _ = start(client, auth_headers, topic)
    clock[0] += timedelta(seconds=100)
    state = apply(client, auth_headers, state, kind="pass")
    clock[0] += timedelta(seconds=200)
    state = apply(client, auth_headers, state, kind="pass")
    clock[0] += timedelta(seconds=900)
    state = client.get(f"/pasapalabra/matches/{state['id']}", headers=auth_headers).json()
    assert state["status"] == "FINISHED"
    assert state["finished_at"].startswith("2030-01-01T00:20:00")
    assert [p["remaining_ms"] for p in state["participants"]] == [0, 0]


def test_resolution_order_survives_circular_revisit_and_reload(db, client, topic, auth_headers, clock):
    bank(db, topic)
    state, _ = start(client, auth_headers, topic)
    state = apply(client, auth_headers, state, kind="pass")
    state = apply(client, auth_headers, state, text="incorrecta")
    for _ in range(20):
        state = apply(client, auth_headers, state)
    resolved = [(p["position"], q) for p in state["participants"] for q in p["resolved"]]
    latest = max(resolved, key=lambda entry: entry[1]["resolution_order"])
    assert latest[0] == 1 and latest[1]["number"] == 1
    assert latest[1]["resolution_order"] == state["version"]
    assert len({q["resolution_order"] for _, q in resolved}) == 21
    reloaded = client.get(f"/pasapalabra/matches/{state['id']}", headers=auth_headers).json()
    assert [p["resolved"] for p in reloaded["participants"]] == [p["resolved"] for p in state["participants"]]
