"""Add multiple-choice fields without changing legacy free-text questions."""

from alembic import op
import sqlalchemy as sa


revision = "a71c9e2b340f"
down_revision = "d328143c2ceb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("options", sa.JSON(), nullable=True))
    op.add_column(
        "questions", sa.Column("correct_option_index", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("questions", "correct_option_index")
    op.drop_column("questions", "options")
