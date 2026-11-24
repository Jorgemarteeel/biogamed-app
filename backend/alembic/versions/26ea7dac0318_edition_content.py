"""Scope new content to editions without moving historical questions."""
from alembic import op
import sqlalchemy as sa

revision = "26ea7dac0318"
down_revision = "15df6c9be207"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("topics", sa.Column("edition_id", sa.Integer(), nullable=True))
    op.add_column("topics", sa.Column("icon_data", sa.Text(), nullable=True))
    op.create_foreign_key("fk_topic_edition", "topics", "academic_editions", ["edition_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_topic_edition_name", "topics", ["edition_id", "name"])
    op.create_unique_constraint("uq_topic_id_edition", "topics", ["id", "edition_id"])
    op.add_column("questions", sa.Column("edition_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_question_edition", "questions", "academic_editions", ["edition_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_question_topic_edition", "questions", "topics", ["topic_id", "edition_id"], ["id", "edition_id"], ondelete="RESTRICT")
    op.drop_constraint("ck_question_open_format", "questions", type_="check")
    op.create_check_constraint("ck_question_open_format", "questions",
        "(question_type = 'INMUNOQUEST' AND reference_answer IS NOT NULL AND length(trim(reference_answer)) > 0 "
        "AND difficulty BETWEEN 1 AND 4 AND difficulty IS NOT NULL "
        "AND ((edition_id IS NULL AND topic_id IS NULL AND bank IN ('LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA') AND bank IS NOT NULL) "
        "OR (edition_id IS NOT NULL AND topic_id IS NOT NULL AND bank IS NULL)) "
        "AND (options IS NULL OR options::jsonb = 'null'::jsonb) AND correct_option_index IS NULL AND exact_word IS NULL AND letter IS NULL) "
        "OR (question_type <> 'INMUNOQUEST' AND topic_id IS NOT NULL AND correct_answer IS NOT NULL AND reference_answer IS NULL AND bank IS NULL AND note_reference IS NULL)")
    op.create_index("ix_questions_edition_topic", "questions", ["edition_id", "topic_id"])
    op.create_table("edition_board_topics",
        sa.Column("edition_id", sa.Integer(), sa.ForeignKey("academic_editions.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("bank", sa.String(16), primary_key=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id", "edition_id"], ["topics.id", "topics.edition_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("edition_id", "topic_id"),
        sa.CheckConstraint("bank IN ('LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA')"))


def downgrade():
    raise RuntimeError("No destructive downgrade of edition content. Restore a verified backup instead.")
