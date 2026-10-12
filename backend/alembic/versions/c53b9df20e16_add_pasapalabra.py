"""Add Pasapalabra fields while keeping existing rows as Trivial."""
from alembic import op
import sqlalchemy as sa

revision = "c53b9df20e16"
down_revision = "b42a8cf19d05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column(
        "question_type", sa.String(20), nullable=False, server_default="TRIVIAL",
    ))
    op.add_column("questions", sa.Column("letter", sa.String(1), nullable=True))
    op.add_column("questions", sa.Column("exact_word", sa.String(255), nullable=True))
    op.add_column("game_engine_sessions", sa.Column(
        "game_mode", sa.String(20), nullable=False, server_default="TRIVIAL",
    ))


def downgrade() -> None:
    op.drop_column("game_engine_sessions", "game_mode")
    op.drop_column("questions", "exact_word")
    op.drop_column("questions", "letter")
    op.drop_column("questions", "question_type")
