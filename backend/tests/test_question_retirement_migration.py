"""Explicit disposable PostgreSQL only; never fall back to the application DB."""
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import make_url

import app.database as database


def test_retirement_migration_preserves_content_defaults_and_guards_downgrade(monkeypatch):
    url = os.getenv("TEST_RETIREMENT_POSTGRES_URL")
    if not url:
        pytest.skip("requires explicit TEST_RETIREMENT_POSTGRES_URL")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith("test_biogamed_"):
        pytest.fail("Use a disposable PostgreSQL database named test_biogamed_*")
    schema = "test_retirement_" + uuid.uuid4().hex
    root = create_engine(parsed)
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(parsed, connect_args={"options": f"-csearch_path={schema}"})
    monkeypatch.setattr(database, "engine", engine)
    config = Config("alembic.ini")
    try:
        command.upgrade(config, "d9f65a827bc1")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO topics (id,name) VALUES (1,'Original')"))
            connection.execute(text("INSERT INTO questions (id,text,correct_answer,topic_id,question_type) VALUES (1,'Original T','B',1,'TRIVIAL'),(2,'Original P','Luna',1,'PASAPALABRA')"))
        old = MetaData()
        old.reflect(engine)
        def content():
            with engine.connect() as connection:
                return {name: list(connection.execute(select(table)).mappings()) for name, table in old.tables.items() if name != "alembic_version"}
        before = content()
        command.upgrade(config, "head")
        assert content() == before
        column = next(c for c in inspect(engine).get_columns("questions") if c["name"] == "is_active")
        assert not column["nullable"] and column["default"] == "true"
        with engine.begin() as connection:
            assert connection.execute(text("SELECT is_active FROM questions ORDER BY id")).scalars().all() == [True, True]
            connection.execute(text("INSERT INTO questions (id,text,correct_answer,topic_id) VALUES (3,'New','B',1)"))
            assert connection.scalar(text("SELECT is_active FROM questions WHERE id=3")) is True
            connection.execute(text("UPDATE questions SET is_active=false WHERE id=1"))
        command.check(config)
        with pytest.raises(RuntimeError, match="Cannot discard retired"):
            command.downgrade(config, "d9f65a827bc1")
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT is_active FROM questions WHERE id=1")) is False
            connection.execute(text("UPDATE questions SET is_active=true WHERE id=1"))
        command.downgrade(config, "d9f65a827bc1")
        assert "is_active" not in {c["name"] for c in inspect(engine).get_columns("questions")}
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
