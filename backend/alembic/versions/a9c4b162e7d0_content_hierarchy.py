"""Add optional academic classification alongside legacy topics."""
from alembic import op
import sqlalchemy as sa


revision = "a9c4b162e7d0"
down_revision = "f86ec0153249"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "content_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_content_blocks_subject_id", "content_blocks", ["subject_id"])
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("block_id", sa.Integer(), sa.ForeignKey("content_blocks.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_categories_block_id", "categories", ["block_id"])
    op.add_column("questions", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_questions_category_id", "questions", "categories",
        ["category_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_questions_category_id", "questions", ["category_id"])


def downgrade():
    op.drop_index("ix_questions_category_id", table_name="questions")
    op.drop_constraint("fk_questions_category_id", "questions", type_="foreignkey")
    op.drop_column("questions", "category_id")
    op.drop_index("ix_categories_block_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_content_blocks_subject_id", table_name="content_blocks")
    op.drop_table("content_blocks")
    op.drop_table("subjects")
