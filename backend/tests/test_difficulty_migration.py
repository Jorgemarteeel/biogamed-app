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
from sqlalchemy.orm import Session

import app.database as database
from app.models import Category, ContentBlock, Subject


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
    command.upgrade(config, "f86ec0153249")
    assert snapshot() == before
    column = next(c for c in inspect(engine).get_columns("questions") if c["name"] == "difficulty")
    assert column["nullable"] is True
    assert column["default"] is None
    assert "ck_question_difficulty" in {c["name"] for c in inspect(engine).get_check_constraints("questions")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT difficulty FROM questions ORDER BY id")).scalars().all() == [None, None]
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "f86ec0153249"

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
    command.upgrade(config, "f86ec0153249")
    assert snapshot() == before


def test_content_hierarchy_migration_preserves_history_and_restricts_deletion(migration_engine):
    engine = migration_engine
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "f86ec0153249")

    user_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id,name,email,hashed_password,role) "
            "VALUES (:id,'Existing','existing@example.com','unused','STUDENT')"
        ), {"id": user_id})
        connection.execute(text("INSERT INTO topics (id,name) VALUES (7,'Legacy topic')"))
        connection.execute(text(
            "INSERT INTO questions (id,text,correct_answer,topic_id,question_type,difficulty) "
            "VALUES (11,'Existing Trivial','A',7,'TRIVIAL',2), "
            "(12,'Existing Pasapalabra','A',7,'PASAPALABRA',NULL)"
        ))
        connection.execute(text(
            "INSERT INTO game_engine_sessions "
            "(id,user_id,topic_id,score,is_completed,created_at,question_ids,game_mode) "
            "VALUES (21,:id,7,1,true,now(),'[11]','TRIVIAL'), "
            "(22,:id,7,0,false,now(),'[12]','PASAPALABRA')"
        ), {"id": user_id})
        connection.execute(text(
            "INSERT INTO answer_logs "
            "(id,game_session_id,question_id,question_text,question_type,is_correct,answered_at) "
            "VALUES (31,21,11,'Existing Trivial','TRIVIAL',true,now())"
        ))

    old = MetaData()
    old.reflect(engine)
    names = ("users", "topics", "questions", "game_engine_sessions", "answer_logs")

    def snapshot():
        with engine.connect() as connection:
            return {name: [dict(row) for row in connection.execute(
                select(old.tables[name]).order_by(old.tables[name].c.id)
            ).mappings()] for name in names}

    before = snapshot()
    command.upgrade(config, "a9c4b162e7d0")
    assert snapshot() == before
    inspector = inspect(engine)
    assert {"subjects", "content_blocks", "categories"}.issubset(inspector.get_table_names())
    assert {name: inspector.get_columns(name) for name in ("subjects", "content_blocks", "categories")}
    category_column = next(c for c in inspector.get_columns("questions") if c["name"] == "category_id")
    assert category_column["nullable"] is True and category_column["default"] is None
    for table, column, target in (
        ("content_blocks", "subject_id", "subjects"),
        ("categories", "block_id", "content_blocks"),
        ("questions", "category_id", "categories"),
    ):
        assert any(
            fk["constrained_columns"] == [column] and fk["referred_table"] == target
            and fk["options"].get("ondelete") == "RESTRICT"
            for fk in inspector.get_foreign_keys(table)
        )
        assert any(index["column_names"] == [column] for index in inspector.get_indexes(table))
    assert next(c for c in inspector.get_columns("content_blocks") if c["name"] == "subject_id")["nullable"] is False
    assert next(c for c in inspector.get_columns("categories") if c["name"] == "block_id")["nullable"] is True
    with engine.connect() as connection:
        assert connection.execute(text("SELECT category_id FROM questions ORDER BY id")).scalars().all() == [None, None]
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "a9c4b162e7d0"
        for table in ("subjects", "content_blocks", "categories"):
            assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0

    with engine.begin() as connection:
        connection.execute(text("INSERT INTO subjects (id,name) VALUES (1,'Illustrative subject')"))
        connection.execute(text("INSERT INTO content_blocks (id,subject_id,name) VALUES (2,1,'Illustrative block')"))
        connection.execute(text("INSERT INTO categories (id,block_id,name) VALUES (3,2,'Illustrative category'), (4,NULL,'Unplaced')"))
        connection.execute(text("UPDATE questions SET category_id=3 WHERE id=11"))
    for model, identifier, children in (
        (Subject, 1, "blocks"),
        (ContentBlock, 2, "categories"),
        (Category, 3, "questions"),
    ):
        with Session(engine) as session:
            parent = session.get(model, identifier)
            assert getattr(parent, children)
            session.delete(parent)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    for statement in (
        "DELETE FROM subjects WHERE id=1",
        "DELETE FROM content_blocks WHERE id=2",
        "DELETE FROM categories WHERE id=3",
        "INSERT INTO content_blocks (subject_id,name) VALUES (999,'Orphan')",
        "UPDATE questions SET category_id=999 WHERE id=12",
    ):
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(statement))
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM answer_logs")) == 1
        assert connection.scalar(text("SELECT category_id FROM questions WHERE id=11")) == 3

    # Remove only test classification so a downgrade can prove legacy rows survive.
    with engine.begin() as connection:
        connection.execute(text("UPDATE questions SET category_id=NULL WHERE id=11"))
        connection.execute(text("DELETE FROM categories"))
        connection.execute(text("DELETE FROM content_blocks"))
        connection.execute(text("DELETE FROM subjects"))
    assert snapshot() == before
    command.check(config)
    command.downgrade(config, "f86ec0153249")
    assert snapshot() == before
    assert "category_id" not in {c["name"] for c in inspect(engine).get_columns("questions")}
