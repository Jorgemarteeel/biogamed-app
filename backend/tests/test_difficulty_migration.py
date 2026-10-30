"""Opt-in migration test: requires an explicitly supplied disposable PostgreSQL DB."""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

import app.database as database


@pytest.fixture
def migration_engine(monkeypatch):
    url = os.getenv("TEST_DIFFICULTY_POSTGRES_URL")
    if not url:
        pytest.skip("requires TEST_DIFFICULTY_POSTGRES_URL pointing to a disposable database")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith("test_biogamed_"):
        pytest.fail("Use a disposable PostgreSQL database named test_biogamed_*, never the development DB")
    # No fallback to the application's database URL, and a unique schema per run.
    schema = "test_difficulty_" + uuid.uuid4().hex
    root_engine = create_engine(parsed)
    with root_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(parsed, connect_args={"options": f"-csearch_path={schema}"})
    monkeypatch.setattr(database, "engine", engine)
    try:
        yield engine
    finally:
        engine.dispose()
        try:
            with root_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            root_engine.dispose()


def test_difficulty_migration_preserves_existing_data(migration_engine):
    engine = migration_engine
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "e75dbf042138")
    old_metadata = MetaData()
    old_metadata.reflect(engine)
    tables = {name: old_metadata.tables[name] for name in (
        "users", "topics", "questions", "game_engine_sessions", "answer_logs",
    )}
    user_id = uuid.uuid4()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with engine.begin() as connection:
        connection.execute(tables["users"].insert(), {
            "id": user_id, "name": "Migration Test", "email": "migration@example.com",
            "hashed_password": "test-only-unused", "role": "STUDENT",
        })
        connection.execute(tables["topics"].insert(), {"id": 7, "name": "Existing topic", "description": "Keep"})
        for question_id, mode in [(11, "TRIVIAL"), (12, "PASAPALABRA")]:
            trivial = mode == "TRIVIAL"
            connection.execute(tables["questions"].insert(), {
                "id": question_id, "text": "Existing " + mode, "correct_answer": "Aorta",
                "topic_id": 7, "question_type": mode, "options": ["Aorta", "B", "C", "D"] if trivial else None,
                "correct_option_index": 0 if trivial else None, "game_letter": None if trivial else "A",
                "letter": None if trivial else "A", "exact_word": None if trivial else "Aorta",
                "accepted_answers": None if trivial else ["arteria aorta"],
            })
            connection.execute(tables["game_engine_sessions"].insert(), {
                "id": question_id, "user_id": user_id, "topic_id": 7, "score": 1,
                "is_completed": True, "created_at": now, "question_ids": [question_id], "game_mode": mode,
            })
            connection.execute(tables["answer_logs"].insert(), {
                "id": question_id, "game_session_id": question_id, "question_id": question_id,
                "question_text": "Historical " + mode, "question_type": mode,
                "options": ["Aorta", "B", "C", "D"] if trivial else None,
                "letter": None if trivial else "A", "selected_index": 0 if trivial else None,
                "text_answer": None if trivial else " AORTA ", "correct_option_index": 0 if trivial else None,
                "exact_word": None if trivial else "Aorta", "is_correct": True,
                "accepted_answers": None if trivial else ["arteria aorta"],
                "response_time_ms": 1200, "answered_at": now,
            })
        connection.execute(tables["game_engine_sessions"].insert(), {
            "id": 13, "user_id": user_id, "topic_id": 7, "score": 0, "is_completed": False,
            "created_at": now, "question_ids": [11], "game_mode": "TRIVIAL",
        })

    def snapshot():
        # Select the pre-migration columns: compare every existing value, not just counts.
        with engine.connect() as connection:
            return {name: [dict(row) for row in connection.execute(
                select(table).order_by(table.c.id)
            ).mappings()] for name, table in tables.items()}

    before = snapshot()
    command.upgrade(config, "head")
    assert snapshot() == before
    column = next(c for c in inspect(engine).get_columns("questions") if c["name"] == "difficulty")
    assert column["nullable"] is True
    assert column["default"] is None
    assert "ck_question_difficulty" in {c["name"] for c in inspect(engine).get_check_constraints("questions")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT difficulty FROM questions ORDER BY id")).scalars().all() == [None, None]
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "f86ec0153249"
    command.check(config)

    for value in [-1, 0, 5]:
        with pytest.raises(IntegrityError, match="ck_question_difficulty"):
            with engine.begin() as connection:
                connection.execute(text("UPDATE questions SET difficulty=:value WHERE id=11"), {"value": value})
    for value in [1, 2, 3, 4, None]:
        with engine.begin() as connection:
            connection.execute(text("UPDATE questions SET difficulty=:value WHERE id=11"), {"value": value})
            assert connection.scalar(text("SELECT difficulty FROM questions WHERE id=11")) == value
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO questions (id,text,correct_answer,topic_id) VALUES (14,'No level','A',7)"
        ))
        assert connection.scalar(text("SELECT difficulty FROM questions WHERE id=14")) is None
        connection.execute(text("DELETE FROM questions WHERE id=14"))
    assert snapshot() == before
    command.downgrade(config, "e75dbf042138")
    assert "difficulty" not in {c["name"] for c in inspect(engine).get_columns("questions")}
    assert snapshot() == before
    command.upgrade(config, "head")
    assert snapshot() == before
