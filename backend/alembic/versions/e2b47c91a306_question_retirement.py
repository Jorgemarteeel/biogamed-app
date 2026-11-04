"""Keep questions while excluding retired content from new games."""
from alembic import op
import sqlalchemy as sa

revision = "e2b47c91a306"
down_revision = "d9f65a827bc1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    questions = sa.table("questions", sa.column("is_active", sa.Boolean()))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(questions).where(questions.c.is_active.is_(False))):
        raise RuntimeError("Cannot discard retired question state: reactivate questions before downgrade.")
    op.drop_column("questions", "is_active")
