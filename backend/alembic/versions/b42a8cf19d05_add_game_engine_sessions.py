"""Add sessions for the multiple-choice game engine."""
from alembic import op
import sqlalchemy as sa

revision = "b42a8cf19d05"
down_revision = "a71c9e2b340f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recover installations where the previous startup create_all created this
    # table before Alembic could record the revision. Offline SQL stays explicit.
    if not op.get_context().as_sql:
        inspector = sa.inspect(op.get_bind())
        if inspector.has_table("game_engine_sessions"):
            _validate_existing_table(inspector)
            return
    op.create_table(
        "game_engine_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("question_ids", sa.JSON(), nullable=False),
    )


def _validate_existing_table(inspector) -> None:
    expected = {
        "id": sa.Integer,
        "user_id": sa.Uuid,
        "topic_id": sa.Integer,
        "score": sa.Integer,
        "is_completed": sa.Boolean,
        "created_at": sa.DateTime,
        "question_ids": sa.JSON,
    }
    columns = {
        column["name"]: column
        for column in inspector.get_columns("game_engine_sessions")
    }
    valid = set(columns) == set(expected)
    valid = valid and all(
        isinstance(columns[name]["type"], column_type)
        and not columns[name]["nullable"]
        for name, column_type in expected.items()
    )
    valid = valid and columns["created_at"]["type"].timezone
    valid = valid and inspector.get_pk_constraint("game_engine_sessions")[
        "constrained_columns"
    ] == ["id"]
    foreign_keys = {
        (tuple(fk["constrained_columns"]), fk["referred_table"],
         tuple(fk["referred_columns"]))
        for fk in inspector.get_foreign_keys("game_engine_sessions")
    }
    valid = valid and {
        (("user_id",), "users", ("id",)),
        (("topic_id",), "topics", ("id",)),
    }.issubset(foreign_keys)
    if not valid:
        raise RuntimeError(
            "game_engine_sessions already exists with an unexpected schema; "
            "migration stopped without changing its data."
        )


def downgrade() -> None:
    op.drop_table("game_engine_sessions")
