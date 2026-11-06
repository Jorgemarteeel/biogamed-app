from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, func

from app.models import User, Topic, Question, Category, GameSession, AnswerLog, UserRole
from app.models.pasapalabra import PasapalabraMatch, PasapalabraRoom, MatchQuestion
from app.schemas.pasapalabra import RoomCreate, RoomJoin, RoomAction, Answer, Command, Abandon
from app.services import pasapalabra as engine, pasapalabra_rooms as rooms
from app.services.game import get_game_progress, get_game_history_detail


@pytest.fixture
def online_bank(db, monkeypatch):
    clock = [datetime(2030, 1, 1, tzinfo=timezone.utc)]
    monkeypatch.setattr(engine, "server_now", lambda db: clock[0])
    monkeypatch.setattr(engine.RNG, "choice", lambda values: 1)
    users = [User(name=f"Cuenta {i}", email=f"online-{i}@example.test", hashed_password="unused",
                  role=UserRole.ADMIN if i == 3 else UserRole.STUDENT) for i in range(4)]
    topic, category = Topic(name="Temática ficticia"), Category(name="Categoría ficticia")
    db.add_all([*users, topic, category])
    db.flush()
    db.add_all([Question(topic_id=topic.id, category_id=category.id, difficulty=2,
                         question_type="PASAPALABRA", text=f"Pista secreta {i}",
                         exact_word="Aorta", correct_answer="Aorta", letter="A", accepted_answers=["Arteria"])
                for i in range(40)])
    db.commit()
    return users, topic, category, clock


def lobby(db, users, topic, category):
    owner, guest = users[:2]
    room = rooms.create(db, owner, RoomCreate(operation_id=uuid4(), topic_id=topic.id, category_id=category.id, difficulty=2))
    room = rooms.join(db, guest, RoomJoin(operation_id=uuid4(), code=room["code"]))
    return room


def ready(db, actor, room):
    return rooms.action(db, actor, room["id"], "ready", RoomAction(operation_id=uuid4(), expected_version=room["version"]))


def started(db, users, topic, category):
    room = lobby(db, users, topic, category)
    room = ready(db, users[0], room)
    room = ready(db, users[1], room)
    return rooms.action(db, users[0], room["id"], "start", RoomAction(operation_id=uuid4(), expected_version=room["version"]))


def test_room_retry_accounts_ready_leave_rejoin_cancel(db, online_bank):
    users, topic, category, _ = online_bank
    request = RoomCreate(operation_id=uuid4(), topic_id=topic.id)
    room = rooms.create(db, users[0], request)
    assert rooms.create(db, users[0], request)["id"] == room["id"]
    with pytest.raises(HTTPException) as exc:
        rooms.join(db, users[0], RoomJoin(operation_id=uuid4(), code=room["code"]))
    assert exc.value.detail["code"] == "DISTINCT_ACCOUNT_REQUIRED"
    join = RoomJoin(operation_id=uuid4(), code=room["code"].lower())
    room = rooms.join(db, users[1], join)
    assert rooms.join(db, users[1], join)["version"] == room["version"]
    room = ready(db, users[0], room)
    leave = RoomAction(operation_id=uuid4(), expected_version=room["version"])
    assert rooms.action(db, users[1], room["id"], "leave", leave)["status"] == "LEFT"
    assert rooms.action(db, users[1], room["id"], "leave", leave)["status"] == "LEFT"
    room = rooms.read(db, users[0], room["id"])
    assert not room["participants"][0]["ready"] and len(room["participants"]) == 1
    with pytest.raises(HTTPException):
        rooms.join(db, users[1], join)  # Old retry cannot acquire the freed seat.
    room = rooms.join(db, users[2], RoomJoin(operation_id=uuid4(), code=room["code"]))
    assert not any(p["ready"] for p in room["participants"])
    with pytest.raises(HTTPException):
        rooms.read(db, users[1], room["id"])
    room = rooms.action(db, users[0], room["id"], "cancel", RoomAction(operation_id=uuid4(), expected_version=room["version"]))
    assert room["status"] == "CANCELLED" and room["code"] is None
    with pytest.raises(HTTPException):
        ready(db, users[2], room)
    assert db.scalar(select(func.count()).select_from(GameSession)) == 0


def test_fixed_expiry_and_join_throttle(db, online_bank):
    users, topic, _, clock = online_bank
    room = rooms.create(db, users[0], RoomCreate(operation_id=uuid4(), topic_id=topic.id))
    expires = room["expires_at"]
    for _ in range(10):
        with pytest.raises(HTTPException) as exc:
            rooms.join(db, users[1], RoomJoin(operation_id=uuid4(), code="INCORRECTO"))
        assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        rooms.join(db, users[1], RoomJoin(operation_id=uuid4(), code=room["code"]))
    assert exc.value.status_code == 429
    clock[0] += timedelta(minutes=10)
    room = rooms.join(db, users[1], RoomJoin(operation_id=uuid4(), code=room["code"]))
    assert engine.utc(room["expires_at"]) == engine.utc(expires)
    clock[0] += timedelta(minutes=20)
    room = rooms.read(db, users[1], room["id"])
    assert room["status"] == "EXPIRED"
    with pytest.raises(HTTPException):
        ready(db, users[0], room)


def test_start_revalidates_bank_and_needs_both_ready(db, online_bank):
    users, topic, category, _ = online_bank
    room = lobby(db, users, topic, category)
    with pytest.raises(HTTPException):
        rooms.action(db, users[0], room["id"], "start", RoomAction(operation_id=uuid4(), expected_version=room["version"]))
    room = ready(db, users[0], room)
    room = ready(db, users[1], room)
    question = db.scalar(select(Question))
    question.is_active = False
    db.commit()
    with pytest.raises(HTTPException) as exc:
        rooms.action(db, users[0], room["id"], "start", RoomAction(operation_id=uuid4(), expected_version=room["version"]))
    assert exc.value.detail["code"] == "INSUFFICIENT_QUESTIONS"
    assert exc.value.detail["available"] == 39
    db.rollback()
    assert rooms.read(db, users[0], room["id"])["status"] == "WAITING"
    assert db.scalar(select(func.count()).select_from(PasapalabraMatch)) == 0


def test_online_privacy_self_actions_history_and_forfeit(db, online_bank):
    users, topic, category, _ = online_bank
    room = started(db, users, topic, category)
    match_id = room["match_id"]
    first = engine.read_state(db, users[0], match_id)
    second = engine.read_state(db, users[1], match_id)
    assert first["play_mode"] == "ONLINE" and second["self_position"] == 2
    assert first["active_question"] and second["active_question"] is None
    assert first["personal_session_id"] != second["personal_session_id"]
    assert "Pista secreta" not in str(second) and "Aorta" not in str(second)
    assert len({q.question_id for q in db.scalars(select(MatchQuestion))}) == 40
    for stranger in users[2:]:
        with pytest.raises(HTTPException):
            engine.read_state(db, stranger, match_id)
        with pytest.raises(HTTPException):
            rooms.read(db, stranger, room["id"])
    with pytest.raises(HTTPException) as exc:
        engine.execute(db, users[0], match_id, "answer", Answer(operation_id=uuid4(), expected_version=first["version"], participant=2, number=1, text_answer="Aorta"))
    assert exc.value.status_code == 403
    first = engine.execute(db, users[0], match_id, "answer", Answer(operation_id=uuid4(), expected_version=first["version"], participant=1, number=1, text_answer="Aorta"))["state"]
    second = engine.read_state(db, users[1], match_id)
    assert first["participants"][0]["resolved"] and second["participants"][0]["resolved"] == []
    assert "Aorta" not in str(second)
    own = engine.execute(db, users[1], match_id, "abandon", Abandon(operation_id=uuid4(), expected_version=second["version"], participant=2))["state"]
    assert own["winner_position"] == 1 and own["outcome"] == "ABANDONMENT"
    assert get_game_history_detail(db, users[0], first["personal_session_id"]).score == 1
    with pytest.raises(HTTPException):
        get_game_history_detail(db, users[1], first["personal_session_id"])
    for user in users[:2]:
        stats = get_game_progress(db, user)
        assert stats["started"] == stats["unfinished"] == 1 and stats["best_marks"] == []


def test_online_tie_and_individual_marks(db, online_bank):
    users, topic, category, _ = online_bank
    room = started(db, users, topic, category)
    state = engine.read_state(db, users[0], room["match_id"])
    for _ in range(40):
        actor = users[state["active_participant"] - 1]
        state = engine.read_state(db, actor, room["match_id"])
        q = state["active_question"]
        state = engine.execute(db, actor, room["match_id"], "answer", Answer(operation_id=uuid4(), expected_version=state["version"], participant=q["participant"], number=q["number"], text_answer="Arteria"))["state"]
    assert state["winner_position"] is None and state["status"] == "FINISHED"
    for user in users[:2]:
        stats = get_game_progress(db, user)
        assert stats["started"] == stats["completed"] == 1
        assert stats["best_marks"][0]["format_key"] == "pasapalabra-online-v1"
        personal = engine.read_state(db, user, room["match_id"])
        assert sum(len(p["resolved"]) for p in personal["participants"]) == 20
        assert len(get_game_history_detail(db, user, personal["personal_session_id"]).answer_logs) == 20


def test_online_clock_recovery_and_deadline_precedence(db, online_bank):
    users, topic, category, clock = online_bank
    room = started(db, users, topic, category)
    state = engine.read_state(db, users[0], room["match_id"])
    clock[0] += timedelta(minutes=10)
    with pytest.raises(HTTPException):
        engine.execute(db, users[0], room["match_id"], "answer", Answer(operation_id=uuid4(), expected_version=state["version"], participant=1, number=1, text_answer="Aorta"))
    recovered = engine.read_state(db, users[1], room["match_id"])
    assert recovered["active_question"]["participant"] == 2
    assert recovered["participants"][0]["finish_reason"] == "TIMEOUT"
    clock[0] += timedelta(minutes=10)
    for user in users[:2]:
        ended = engine.read_state(db, user, room["match_id"])
        assert ended["status"] == "FINISHED" and ended["winner_position"] is None
        assert all(p["pending"] == 20 and p["wrong"] == 0 for p in ended["participants"])


def test_expiry_during_start_selection_is_durable(db, online_bank, monkeypatch):
    users, topic, category, clock = online_bank
    room = lobby(db, users, topic, category)
    room = ready(db, users[0], room)
    room = ready(db, users[1], room)
    clock[0] += timedelta(minutes=29, seconds=59)
    original = engine.RNG.sample
    def delayed_selection(candidates, count):
        clock[0] += timedelta(seconds=1)
        return original(candidates, count)
    monkeypatch.setattr(engine.RNG, "sample", delayed_selection)
    with pytest.raises(HTTPException) as exc:
        rooms.action(db, users[0], room["id"], "start", RoomAction(operation_id=uuid4(), expected_version=room["version"]))
    assert exc.value.detail["code"] == "ROOM_EXPIRED"
    assert rooms.read(db, users[0], room["id"])["status"] == "EXPIRED"
    assert db.scalar(select(func.count()).select_from(GameSession)) == 0


def test_http_contract_auth_privacy_and_code_is_not_authority(db, client, online_bank):
    from app.main import app
    from app.dependencies import get_current_user
    users, topic, category, _ = online_bank
    assert client.post("/pasapalabra/rooms", json={"operation_id": str(uuid4()), "topic_id": topic.id}).status_code == 401
    room = started(db, users, topic, category)
    code = db.get(PasapalabraRoom, room["id"]).code
    previous = app.dependency_overrides.copy()
    try:
        app.dependency_overrides[get_current_user] = lambda: users[1]
        state = client.get(f"/pasapalabra/matches/{room['match_id']}").json()
        assert state["self_position"] == 2 and state["active_question"] is None
        assert state["play_mode"] == "ONLINE" and "snapshot" not in str(state)
        response = client.post(f"/pasapalabra/matches/{room['match_id']}/answer", json={
            "operation_id": str(uuid4()), "expected_version": state["version"], "participant": 1,
            "number": 1, "text_answer": "Aorta"})
        assert response.status_code == 403
        own = client.get(f"/game/history/{state['personal_session_id']}").json()
        assert own["shared_summary"]["self_position"] == 2
        assert "resolved" not in str(own["shared_summary"]) and "text_answer" not in str(own["shared_summary"])
        app.dependency_overrides[get_current_user] = lambda: users[3]  # Admin does not bypass membership.
        for path in [f"/pasapalabra/rooms/{room['id']}", f"/pasapalabra/matches/{room['match_id']}", f"/pasapalabra/matches/{room['match_id']}/result"]:
            assert client.get(path).status_code == 404
        assert client.post("/pasapalabra/rooms/join", json={"operation_id": str(uuid4()), "code": code}).status_code == 404
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_join_rejections_distinguish_auth_account_full_invalid_expired_and_cancelled(db, client, online_bank):
    from app.main import app
    from app.dependencies import get_current_user
    users, topic, _, clock = online_bank
    room = rooms.create(db, users[0], RoomCreate(operation_id=uuid4(), topic_id=topic.id))
    def join_request(code):
        return client.post("/pasapalabra/rooms/join", json={"code": code, "operation_id": str(uuid4())})
    assert join_request(room["code"]).json() == {"detail": "Not authenticated"}
    previous = app.dependency_overrides.copy()
    try:
        app.dependency_overrides[get_current_user] = lambda: users[0]
        response = join_request(room["code"])
        assert response.status_code == 409 and response.json()["detail"]["code"] == "DISTINCT_ACCOUNT_REQUIRED"
        app.dependency_overrides[get_current_user] = lambda: users[1]
        assert join_request("INCORRECTO").status_code == 404
        assert join_request(room["code"]).status_code == 200
        app.dependency_overrides[get_current_user] = lambda: users[2]
        response = join_request(room["code"])
        assert response.status_code == 409 and response.json()["detail"]["code"] == "ROOM_FULL"
        clock[0] += timedelta(minutes=30)
        response = join_request(room["code"])
        assert response.status_code == 409 and response.json()["detail"]["code"] == "ROOM_EXPIRED"
        cancelled = rooms.create(db, users[0], RoomCreate(operation_id=uuid4(), topic_id=topic.id))
        rooms.action(db, users[0], cancelled["id"], "cancel", RoomAction(operation_id=uuid4(), expected_version=cancelled["version"]))
        response = join_request(cancelled["code"])
        assert response.status_code == 409 and response.json()["detail"]["code"] == "ROOM_CANCELLED"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
