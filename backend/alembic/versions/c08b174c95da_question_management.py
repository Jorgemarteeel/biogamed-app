"""Direct academic destinations and removal of unused manual activities.

b97a063b84c9 remains unchanged because it was applied in isolated review.
"""
from alembic import op
import sqlalchemy as sa
revision = "c08b174c95da"
down_revision = "b97a063b84c9"
branch_labels = depends_on = None

def upgrade():
    op.add_column("questions", sa.Column("subject_id", sa.Integer(), nullable=True))
    op.add_column("questions", sa.Column("block_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_question_subject", "questions", "subjects", ["subject_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_question_block", "questions", "content_blocks", ["block_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_questions_subject_id", "questions", ["subject_id"])
    op.create_index("ix_questions_block_id", "questions", ["block_id"])
    # Only real FK chains establish an association. Names and Topic are irrelevant.
    op.execute("UPDATE questions q SET subject_id=b.subject_id, block_id=b.id FROM categories c JOIN content_blocks b ON b.id=c.block_id WHERE q.category_id=c.id")
    op.drop_table("inmunoquest_configurations")

def downgrade():
    raise RuntimeError("Restore an isolated backup instead: do not discard explicit academic destinations or reconstruct removed activities")
