from unittest.mock import patch
from alembic import command
from alembic.config import Config
from sqlalchemy import text, inspect
from migration_fixtures import origin_schema
from test_pasapalabra_postgres import postgres


def test_edition_migration_preserves_legacy_and_has_scoped_constraints(postgres):
    with origin_schema(postgres, "15df6c9be207") as engine:
        with engine.begin() as c:
            c.execute(text("INSERT INTO topics(name) VALUES ('Historical topic')"))
            c.execute(text("INSERT INTO questions(text,question_type,difficulty,topic_id,correct_answer) VALUES ('Historical', 'TRIVIAL', 2, (SELECT id FROM topics LIMIT 1), 'Stored')"))
        with patch("app.database.engine", engine):
            command.upgrade(Config("alembic.ini"), "head")
        with engine.connect() as c:
            assert c.execute(text("SELECT text,edition_id FROM questions")).one() == ("Historical", None)
            assert c.execute(text("SELECT name,edition_id,icon_data FROM topics")).one() == ("Historical topic", None, None)
        assert "edition_board_topics" in inspect(engine).get_table_names()
        assert any(f["name"] == "fk_question_topic_edition" for f in inspect(engine).get_foreign_keys("questions"))
