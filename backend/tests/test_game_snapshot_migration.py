"""Run only with an explicit test_biogamed_* PostgreSQL database; no app URL fallback."""

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import make_url

import app.database as database


@pytest.fixture
def snapshot_migration_engine(monkeypatch):
    url = os.getenv("TEST_GAME_SNAPSHOT_POSTGRES_URL")
    if not url:
        pytest.skip("requires explicit TEST_GAME_SNAPSHOT_POSTGRES_URL")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith("test_biogamed_"):
        pytest.fail("Use a disposable PostgreSQL database named test_biogamed_*")
    schema = "test_snapshot_" + uuid.uuid4().hex
    root = create_engine(parsed)
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(parsed, connect_args={"options": f"-csearch_path={schema}"})
    monkeypatch.setattr(database, "engine", engine)
    try:
        yield engine
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def test_migration_preserves_old_content_without_backfill_and_guards_downgrade(snapshot_migration_engine):
    engine = snapshot_migration_engine
    config = Config("alembic.ini")
    command.upgrade(config, "c8e54b739a21")
    user_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO topics (id,name) VALUES (1,'Original topic')"))
        conn.execute(text("INSERT INTO users (id,name,email,hashed_password,role) VALUES (:id,'Test','snapshot@example.com','unused','STUDENT')"), {"id": user_id})
        conn.execute(text("INSERT INTO questions (id,text,correct_answer,topic_id,difficulty) VALUES (1,'Original question','B',1,2)"))
        conn.execute(text("INSERT INTO game_engine_sessions (id,user_id,topic_id,score,is_completed,created_at,question_ids) VALUES (1,:id,1,1,true,now(),'[1]'), (2,:id,1,0,false,now(),'[1]')"), {"id": user_id})
        conn.execute(text("INSERT INTO answer_logs (game_session_id,question_id,question_text,question_type,is_correct,answered_at) VALUES (1,1,'Saved at correction','TRIVIAL',true,now())"))
    old = MetaData()
    old.reflect(engine)
    names = ("users", "topics", "questions", "game_engine_sessions", "answer_logs")

    def read_old():
        with engine.connect() as conn:
            return {name: [dict(row) for row in conn.execute(select(old.tables[name]).order_by(old.tables[name].c.id)).mappings()]
                    for name in names}

    before = read_old()
    command.upgrade(config, "head")
    assert read_old() == before
    column = next(c for c in inspect(engine).get_columns("game_engine_sessions") if c["name"] == "question_snapshot")
    assert column["nullable"] and column["default"] is None
    with engine.connect() as conn:
        assert conn.execute(text("SELECT question_snapshot FROM game_engine_sessions ORDER BY id")).scalars().all() == [None, None]
    command.check(config)
    command.downgrade(config, "c8e54b739a21")
    assert read_old() == before
    command.upgrade(config, "head")
    with engine.begin() as conn:
        conn.execute(text("UPDATE game_engine_sessions SET question_snapshot=CAST(:snapshot AS JSON) WHERE id=2"),
                     {"snapshot": '{"version":1,"questions":[]}'})
    with pytest.raises(RuntimeError, match="Cannot discard question snapshots"):
        command.downgrade(config, "c8e54b739a21")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT question_snapshot FROM game_engine_sessions WHERE id=2")) == {"version": 1, "questions": []}
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "e2b47c91a306"
    assert read_old() == before
