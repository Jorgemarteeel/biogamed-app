"""Allow academic sessions without a single legacy topic."""
from alembic import op
import sqlalchemy as sa


revision = "b31c40d52e63"
down_revision = "a21b30c41d52"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("game_engine_sessions", "topic_id", existing_type=sa.Integer(), nullable=True)

def downgrade():
    if op.get_bind().scalar(sa.text("select count(*) from game_engine_sessions where topic_id is null")):
        raise RuntimeError("Academic history must be preserved")
    op.alter_column("game_engine_sessions", "topic_id", existing_type=sa.Integer(), nullable=False)
