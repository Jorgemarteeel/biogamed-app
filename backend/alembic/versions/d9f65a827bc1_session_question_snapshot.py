"""Preserve private question content at game start; never backfill old games."""

from alembic import op
import sqlalchemy as sa


revision = "d9f65a827bc1"
down_revision = "c8e54b739a21"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("game_engine_sessions", sa.Column("question_snapshot", sa.JSON(), nullable=True))


def downgrade():
    sessions = sa.table("game_engine_sessions", sa.column("question_snapshot", sa.JSON()))
    if any(value is not None for value in op.get_bind().execute(
        sa.select(sessions.c.question_snapshot)
    ).scalars()):
        raise RuntimeError("Cannot discard question snapshots: archive protected sessions before downgrade.")
    op.drop_column("game_engine_sessions", "question_snapshot")
