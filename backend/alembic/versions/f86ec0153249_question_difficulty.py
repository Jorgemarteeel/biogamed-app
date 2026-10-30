"""Add optional source difficulty without backfilling existing questions."""
from alembic import op
import sqlalchemy as sa


revision = "f86ec0153249"
down_revision = "e75dbf042138"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("difficulty", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_question_difficulty", "questions",
        "difficulty IS NULL OR difficulty BETWEEN 1 AND 4",
    )


def downgrade():
    op.drop_constraint("ck_question_difficulty", "questions", type_="check")
    op.drop_column("questions", "difficulty")
