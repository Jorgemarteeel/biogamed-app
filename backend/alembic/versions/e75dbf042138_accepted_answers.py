"""Store explicit alternative answers and their history snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "e75dbf042138"
down_revision = "d64caef31027"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("accepted_answers", sa.JSON(), nullable=True))
    op.add_column("answer_logs", sa.Column("accepted_answers", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("answer_logs", "accepted_answers")
    op.drop_column("questions", "accepted_answers")
