"""Snapshot selected filters and question classifications for new games."""

from alembic import op
import sqlalchemy as sa


revision = "c8e54b739a21"
down_revision = "a9c4b162e7d0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("game_engine_sessions", sa.Column("content_context", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("game_engine_sessions", "content_context")
