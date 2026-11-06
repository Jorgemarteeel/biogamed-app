from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from test_pasapalabra_postgres import postgres
from app.models import User, Topic, Question, GameSession
from app.models.pasapalabra import PasapalabraMatch, PasapalabraRoom, MatchQuestion, MatchCommand
from app.schemas.pasapalabra import RoomCreate, RoomJoin, RoomAction, Answer, Command
from app.services import pasapalabra as engine, pasapalabra_rooms as rooms


def seed(pg):
    with Session(pg) as db:
        users = [User(name=f"Carrera {i}", email=f"race-{i}@example.test", hashed_password="unused") for i in range(3)]
        topic = Topic(name="Banco aislado")
        db.add_all([*users, topic])
        db.flush()
        db.add_all([Question(topic_id=topic.id, text=f"Privada {i}", question_type="PASAPALABRA", letter="A", exact_word="Aorta", correct_answer="Aorta") for i in range(40)])
        db.commit()
        room = rooms.create(db, users[0], RoomCreate(operation_id=uuid4(), topic_id=topic.id))
        return [u.id for u in users], room


def race(pg, users, invoke):
    barrier = Barrier(2)
    def run(index):
        with Session(pg) as db:
            actor = db.get(User, users[index])
            barrier.wait(timeout=10)
            try:
                return invoke(db, actor, index)
            except HTTPException as exc:
                return exc.status_code, exc.detail
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(run, [0, 1]))


@pytest.mark.parametrize("same_actor", [False, True])
def test_second_seat_race_and_join_retry(postgres, same_actor):
    users, room = seed(postgres)
    operation = uuid4()
    outcomes = race(postgres, [users[1], users[1] if same_actor else users[2]],
                    lambda db, actor, i: rooms.join(db, actor, RoomJoin(operation_id=operation if same_actor else uuid4(), code=room["code"])))
    assert sum(isinstance(o, dict) for o in outcomes) == (2 if same_actor else 1)
    with Session(postgres) as db:
        saved = db.get(PasapalabraRoom, room["id"])
        assert saved.guest_id in users[1:] and saved.version == 2
        assert db.scalar(select(func.count()).select_from(GameSession)) == 0


@pytest.mark.parametrize("same_key", [False, True])
def test_start_race_creates_one_match_and_two_sessions(postgres, same_key):
    users, room = seed(postgres)
    with Session(postgres) as db:
        owner, guest = db.get(User, users[0]), db.get(User, users[1])
        room = rooms.join(db, guest, RoomJoin(operation_id=uuid4(), code=room["code"]))
        for actor in [owner, guest]:
            room = rooms.action(db, actor, room["id"], "ready", RoomAction(operation_id=uuid4(), expected_version=room["version"]))
    operation = uuid4()
    outcomes = race(postgres, [users[0], users[0]], lambda db, actor, i: rooms.action(
        db, actor, room["id"], "start", RoomAction(operation_id=operation if same_key else uuid4(), expected_version=room["version"])))
    assert sum(isinstance(o, dict) for o in outcomes) == (2 if same_key else 1)
    with Session(postgres) as db:
        assert db.scalar(select(func.count()).select_from(PasapalabraMatch)) == 1
        assert db.scalar(select(func.count()).select_from(GameSession)) == 2
        assert len(set(db.scalars(select(MatchQuestion.question_id)))) == 40


@pytest.mark.parametrize("race_kind", ["same_id", "two_answers", "answer_pass"])
def test_create_retry_and_online_answer_pass_race(postgres, race_kind):
    users, original = seed(postgres)
    with Session(postgres) as db:
        topic_id = db.scalar(select(Topic.id))
    request = RoomCreate(operation_id=uuid4(), topic_id=topic_id)
    outcomes = race(postgres, [users[0], users[0]], lambda db, actor, i: rooms.create(db, actor, request))
    assert outcomes[0]["id"] == outcomes[1]["id"]
    room = outcomes[0]
    with Session(postgres) as db:
        owner, guest = db.get(User, users[0]), db.get(User, users[1])
        room = rooms.join(db, guest, RoomJoin(operation_id=uuid4(), code=room["code"]))
        for actor in [owner, guest]:
            room = rooms.action(db, actor, room["id"], "ready", RoomAction(operation_id=uuid4(), expected_version=room["version"]))
        room = rooms.action(db, owner, room["id"], "start", RoomAction(operation_id=uuid4(), expected_version=room["version"]))
        state = engine.read_state(db, owner, room["match_id"])
    answer_id = uuid4()
    def invoke(db, actor, i):
        data = dict(operation_id=answer_id if race_kind == "same_id" else uuid4(), expected_version=state["version"], participant=1, number=1)
        passing = race_kind == "answer_pass" and i == 1
        return engine.execute(db, actor, room["match_id"], "pass" if passing else "answer", Command(**data) if passing else Answer(**data, text_answer="Aorta"))
    outcomes = race(postgres, [users[0], users[0]], invoke)
    assert sum(isinstance(o, dict) for o in outcomes) == (2 if race_kind == "same_id" else 1)
    if race_kind != "same_id":
        assert next(o for o in outcomes if isinstance(o, tuple))[1]["code"] == "STALE_VERSION"
    with Session(postgres) as db:
        assert db.scalar(select(func.count()).select_from(MatchCommand)) == 1


def test_two_room_owners_can_start_without_fk_lock_deadlock(postgres):
    users, first = seed(postgres)
    with Session(postgres) as db:
        a, b = db.get(User, users[0]), db.get(User, users[1])
        second = rooms.create(db, b, RoomCreate(operation_id=uuid4(), topic_id=db.scalar(select(Topic.id))))
        prepared = []
        for room, owner, guest in [(first, a, b), (second, b, a)]:
            room = rooms.join(db, guest, RoomJoin(operation_id=uuid4(), code=room["code"]))
            for actor in [owner, guest]:
                room = rooms.action(db, actor, room["id"], "ready", RoomAction(operation_id=uuid4(), expected_version=room["version"]))
            prepared.append(room)
    outcomes = race(postgres, users[:2], lambda db, actor, i: rooms.action(db, actor, prepared[i]["id"], "start", RoomAction(operation_id=uuid4(), expected_version=prepared[i]["version"])))
    assert all(isinstance(o, dict) and o["status"] == "STARTED" for o in outcomes)


def test_room_migration_schema_and_downgrade_guard(postgres):
    from unittest.mock import patch
    from alembic import command
    from alembic.config import Config
    with patch("app.database.engine", postgres):
        command.check(Config("alembic.ini"))
        command.downgrade(Config("alembic.ini"), "f17a20b30c41")
        command.upgrade(Config("alembic.ini"), "head")
    seed(postgres)
    with patch("app.database.engine", postgres), pytest.raises(RuntimeError, match="Cannot discard private room"):
        command.downgrade(Config("alembic.ini"), "f17a20b30c41")
