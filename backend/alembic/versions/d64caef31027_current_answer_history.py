"""Replace empty legacy game tables with history for the current engine.

Refuse to discard legacy records on installations that still contain them.
Those installations need an explicit data migration before this revision.
"""
from alembic import op
import sqlalchemy as sa

revision = "d64caef31027"
down_revision = "c53b9df20e16"
branch_labels = None
depends_on = None


def require_empty(*tables):
    if op.get_context().as_sql:
        raise RuntimeError("History migration requires an online data check.")
    for name in tables:
        table = sa.table(name)
        if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
            raise RuntimeError(
                f"{name} contains historical data; migrate or archive it before continuing. "
                "No historical records have been deleted."
            )


def upgrade():
    require_empty("answer_logs", "game_sessions")
    op.drop_table("answer_logs")
    op.drop_table("game_sessions")
    sa.Enum(name="answer_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="game_mode").drop(op.get_bind(), checkfirst=True)
    op.create_table(
        "answer_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_engine_sessions.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("letter", sa.String(1), nullable=True),
        sa.Column("selected_index", sa.Integer(), nullable=True),
        sa.Column("text_answer", sa.Text(), nullable=True),
        sa.Column("correct_option_index", sa.Integer(), nullable=True),
        sa.Column("exact_word", sa.String(255), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("game_session_id", "question_id", name="uq_answer_session_question"),
        sa.CheckConstraint("response_time_ms IS NULL OR response_time_ms >= 0", name="ck_answer_response_time"),
    )
    op.create_index("ix_answer_logs_question_id", "answer_logs", ["question_id"])


def downgrade():
    require_empty("answer_logs")
    op.drop_table("answer_logs")
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("game_mode", sa.Enum("TRIVIAL", "PASAPALABRA", name="game_mode"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("final_score", sa.Integer(), nullable=False),
    )
    op.create_table(
        "answer_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("game_session_id", sa.Uuid(), sa.ForeignKey("game_sessions.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("CORRECT", "INCORRECT", "SKIPPED", name="answer_status"), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
    )
