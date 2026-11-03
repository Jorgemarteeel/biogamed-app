"""Opt-in migration check; run against a disposable PostgreSQL server."""

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

import app.database as database


@pytest.mark.skipif(os.getenv("TEST_POSTGRES_MIGRATIONS") != "1", reason="requires PostgreSQL")
def test_content_context_migration_preserves_existing_activity(monkeypatch):
    schema = "test_context_" + uuid.uuid4().hex
    original_engine = database.engine
    with original_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(original_engine.url, connect_args={"options": f"-csearch_path={schema}"})
    monkeypatch.setattr(database, "engine", engine)
    config = Config("alembic.ini")
    try:
        command.upgrade(config, "a9c4b162e7d0")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO topics (id,name) VALUES (1,'Test')"))
            connection.execute(text("INSERT INTO users (id,name,email,hashed_password,role) VALUES (:id,'Test','test@example.com','unused','STUDENT')"), {"id": uuid.uuid4()})
            user_id = connection.scalar(text("SELECT id FROM users WHERE email='test@example.com'"))
            connection.execute(text("INSERT INTO questions (id,text,correct_answer,topic_id,difficulty) VALUES (1,'Question','B',1,2)"))
            connection.execute(text("INSERT INTO game_engine_sessions (id,user_id,topic_id,score,is_completed,created_at,question_ids) VALUES (1,:user,1,1,true,now(),'[1]')"), {"user": user_id})
            connection.execute(text("INSERT INTO answer_logs (game_session_id,question_id,question_text,question_type,is_correct,answered_at) VALUES (1,1,'Question','TRIVIAL',true,now())"))
        command.upgrade(config, "c8e54b739a21")
        column = next(c for c in inspect(engine).get_columns("game_engine_sessions")
                      if c["name"] == "content_context")
        assert column["nullable"] and column["default"] is None
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "c8e54b739a21"
            assert connection.scalar(text("SELECT content_context FROM game_engine_sessions WHERE id=1")) is None
            assert connection.scalar(text("SELECT count(*) FROM questions")) == 1
            assert connection.scalar(text("SELECT count(*) FROM game_engine_sessions")) == 1
            assert connection.scalar(text("SELECT count(*) FROM answer_logs")) == 1
            assert connection.scalar(text("SELECT difficulty FROM questions WHERE id=1")) == 2
        # Compare the current ORM only after applying later migrations too.
        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()
        with original_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
