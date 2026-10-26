"""Opt-in PostgreSQL migration test, isolated in a disposable schema."""
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

import app.database as database


@pytest.mark.skipif(os.getenv("TEST_POSTGRES_MIGRATIONS") != "1", reason="requires PostgreSQL")
def test_history_migration_preserves_data_and_guards_downgrade(monkeypatch):
    schema = "test_history_" + uuid.uuid4().hex
    original_engine = database.engine
    with original_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(original_engine.url, connect_args={"options": f"-csearch_path={schema}"})
    monkeypatch.setattr(database, "engine", engine)
    config = Config("alembic.ini")
    user_id = uuid.uuid4()
    legacy_id = uuid.uuid4()
    try:
        command.upgrade(config, "c53b9df20e16")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users (id,name,email,hashed_password,role) VALUES (:id,'Test','migration@example.com','unused','STUDENT')"), {"id": user_id})
            connection.execute(text("INSERT INTO topics (id,name) VALUES (1,'Test')"))
            connection.execute(text("INSERT INTO questions (id,text,correct_answer,topic_id) VALUES (1,'Question','Answer',1)"))
            connection.execute(text("INSERT INTO game_engine_sessions (id,user_id,topic_id,score,is_completed,created_at,question_ids) VALUES (1,:id,1,3,true,now(),'[1]')"), {"id": user_id})
            connection.execute(text("INSERT INTO game_sessions (id,user_id,game_mode,final_score) VALUES (:id,:user,'TRIVIAL',1)"), {"id": legacy_id, "user": user_id})
        with pytest.raises(RuntimeError, match="historical data"):
            command.upgrade(config, "head")
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT count(*) FROM game_sessions")) == 1
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "c53b9df20e16"
            connection.execute(text("DELETE FROM game_sessions"))
        command.upgrade(config, "head")
        command.check(config)
        assert "game_sessions" not in inspect(engine).get_table_names()
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT score FROM game_engine_sessions WHERE id=1")) == 3
        command.downgrade(config, "c53b9df20e16")
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO answer_logs (game_session_id,question_id,question_text,question_type,is_correct,answered_at) VALUES (1,1,'Question','TRIVIAL',true,now())"))
        with pytest.raises(RuntimeError, match="historical data"):
            command.downgrade(config, "c53b9df20e16")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM answer_logs")) == 1
    finally:
        engine.dispose()
        with original_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
