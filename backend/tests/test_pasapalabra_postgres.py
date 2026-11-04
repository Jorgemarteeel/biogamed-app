"""Real row-lock races. Only an explicitly named disposable database is accepted."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, select, func, text, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import User, Topic, Question, AnswerLog, GameSession
from app.models.pasapalabra import MatchCommand, PasapalabraMatch
from app.schemas.pasapalabra import LocalStart, Answer, Command
from app.services import pasapalabra as service


@pytest.fixture
def postgres(monkeypatch):
    url = os.environ.get("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set TEST_POSTGRES_URL to the verified disposable database")
    parsed = make_url(url)
    if parsed.database != "biogamed_pasapalabra_test" or parsed.username != "codex_test":
        pytest.fail("Refusing PostgreSQL writes outside biogamed_pasapalabra_test / codex_test")
    admin = create_engine(url)
    with admin.connect() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "biogamed_pasapalabra_test"
    schema = "test_pp_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        # Every race runs against the real Alembic schema, not create_all().
        with patch("app.database.engine", engine):
            alembic_command.upgrade(Config("alembic.ini"), "head")
        monkeypatch.setattr(service, "server_now", lambda db: datetime(2030, 1, 1, tzinfo=timezone.utc))
        monkeypatch.setattr(service.RNG, "choice", lambda values: 1)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def setup_match(engine):
    with Session(engine) as db:
        user = User(name="Prueba aislada", email="isolated@example.test", hashed_password="unused")
        topic = Topic(name="Banco ficticio")
        db.add_all([user, topic])
        db.flush()
        db.add_all([Question(topic_id=topic.id, text=f"Ficticia {i}", correct_answer="Aorta",
                             exact_word="Aorta", letter="A", question_type="PASAPALABRA") for i in range(40)])
        db.commit()
        state = service.start_local(db, user, LocalStart(operation_id=uuid4(), topic_id=topic.id, guest_name="Invitado"))
        return user.id, state


@pytest.mark.parametrize("race", ["same_id", "two_answers", "answer_pass"])
def test_real_concurrent_commands(postgres, race):
    user_id, state = setup_match(postgres)
    barrier = Barrier(2)
    operation_id = uuid4()

    def execute(index):
        with Session(postgres) as db:
            owner = db.get(User, user_id)
            kind = "pass" if race == "answer_pass" and index else "answer"
            data = dict(operation_id=operation_id if race == "same_id" else uuid4(),
                        expected_version=state["version"], participant=1, number=1)
            request = Answer(**data, text_answer="Aorta") if kind == "answer" else Command(**data)
            barrier.wait(timeout=10)
            try:
                return service.execute(db, owner, state["id"], kind, request)
            except HTTPException as exc:
                return exc.status_code, exc.detail

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(execute, [0, 1]))
    if race == "same_id":
        assert all(isinstance(item, dict) for item in outcomes)
        assert outcomes[0]["operation"] == outcomes[1]["operation"]
    else:
        assert sum(isinstance(item, dict) for item in outcomes) == 1
        assert next(item for item in outcomes if isinstance(item, tuple)) == (409, {"code": "STALE_VERSION", "version": 2})
    with Session(postgres) as db:
        owner = db.get(User, user_id)
        final = service.read_state(db, owner, state["id"])
        assert final["version"] == 2
        assert db.scalar(select(func.count()).select_from(MatchCommand)) == 1
        assert db.scalar(select(func.count()).select_from(AnswerLog)) <= 1
        assert sum(p["correct"] for p in final["participants"]) <= 1
        # A fresh stale command cannot act on a later question/turn.
        with pytest.raises(HTTPException) as caught:
            service.execute(db, owner, state["id"], "pass", Command(operation_id=uuid4(), expected_version=1, participant=1, number=1))
        assert caught.value.detail["code"] == "STALE_VERSION"


def test_additive_migration_keeps_old_rows_and_guards_downgrade(postgres):
    from app.services.game import start_game_session, submit_game_session
    from app.schemas.game import UserAnswer
    with Session(postgres) as db:
        user = User(name="Legacy", email="legacy@example.test", hashed_password="unused")
        topic = Topic(name="Trivial aislado")
        db.add_all([user, topic])
        db.flush()
        db.add(Question(topic_id=topic.id, text="Ficticia", question_type="TRIVIAL", correct_answer="A",
                        options=["A", "B", "C", "D"], correct_option_index=0))
        db.commit()
        game = start_game_session(db, user, topic.id)
        assert submit_game_session(db, user, game.session_id, [UserAnswer(question_id=game.questions[0].id, selected_index=0)]).score == 1
        session = db.get(GameSession, game.session_id)
        assert session.shared_match_id is None and session.is_completed
    with patch("app.database.engine", postgres):
        alembic_command.downgrade(Config("alembic.ini"), "e2b47c91a306")
    with postgres.connect() as connection:
        assert connection.execute(text("SELECT score,is_completed FROM game_engine_sessions")).one() == (1, True)
    with patch("app.database.engine", postgres):
        alembic_command.upgrade(Config("alembic.ini"), "head")
    assert "shared_match_id" in {c["name"] for c in inspect(postgres).get_columns("game_engine_sessions")}
    setup_match(postgres)
    with patch("app.database.engine", postgres), pytest.raises(RuntimeError, match="Cannot discard"):
        alembic_command.downgrade(Config("alembic.ini"), "e2b47c91a306")
