"""Add shared Pasapalabra matches without rewriting existing game history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f17a20b30c41"
down_revision = "e2b47c91a306"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("pasapalabra_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("start_operation_id", sa.String(36), nullable=False),
        sa.Column("start_payload", sa.JSON(), nullable=False),
        sa.Column("play_mode", sa.String(16), nullable=False),
        sa.Column("rules_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("active_position", sa.Integer()),
        sa.Column("turn_started_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("outcome", sa.String(16)),
        sa.Column("winner_position", sa.Integer()),
        sa.UniqueConstraint("owner_id", "start_operation_id"))
    op.create_index("ix_pasapalabra_matches_owner_id", "pasapalabra_matches", ["owner_id"])
    op.add_column("game_engine_sessions", sa.Column("shared_match_id", sa.Integer(), sa.ForeignKey("pasapalabra_matches.id")))
    for name, type_ in [("format_key", sa.String(40)), ("match_status", sa.String(16)),
                        ("completion_reason", sa.String(24)), ("wrong_count", sa.Integer()),
                        ("pending_count", sa.Integer())]:
        op.add_column("game_engine_sessions", sa.Column(name, type_))
    op.create_index("ix_game_engine_sessions_shared_match_id", "game_engine_sessions", ["shared_match_id"])
    op.create_table("pasapalabra_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("pasapalabra_matches.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("game_engine_sessions.id"), unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("finish_reason", sa.String(24)),
        sa.Column("remaining_ms", sa.Integer(), nullable=False),
        sa.Column("cursor", sa.Integer(), nullable=False),
        sa.UniqueConstraint("match_id", "position"), sa.UniqueConstraint("match_id", "user_id"),
        sa.CheckConstraint("position IN (1, 2)"),
        sa.CheckConstraint("remaining_ms >= 0 AND remaining_ms <= 600000"))
    op.create_index("ix_pasapalabra_participants_match_id", "pasapalabra_participants", ["match_id"])
    op.create_table("pasapalabra_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("pasapalabra_matches.id"), nullable=False),
        sa.Column("participant_id", sa.Integer(), sa.ForeignKey("pasapalabra_participants.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("text_answer", sa.Text()),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.UniqueConstraint("match_id", "question_id"), sa.UniqueConstraint("participant_id", "number"),
        sa.CheckConstraint("number BETWEEN 1 AND 20"),
        sa.CheckConstraint("state IN ('PENDING','PASSED','CORRECT','WRONG')"))
    op.create_index("ix_pasapalabra_questions_participant_id", "pasapalabra_questions", ["participant_id"])
    op.create_table("pasapalabra_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("pasapalabra_matches.id"), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.UniqueConstraint("match_id", "operation_id"))


def downgrade():
    table = sa.table("pasapalabra_matches", sa.column("id", sa.Integer()))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError("Cannot discard shared match history; export it before a destructive downgrade.")
    op.drop_table("pasapalabra_commands")
    op.drop_table("pasapalabra_questions")
    op.drop_table("pasapalabra_participants")
    op.drop_index("ix_game_engine_sessions_shared_match_id", table_name="game_engine_sessions")
    # Name supplied by SQLAlchemy's FK naming convention is not assumed here.
    inspector = sa.inspect(op.get_bind())
    for constraint in inspector.get_foreign_keys("game_engine_sessions"):
        if constraint["constrained_columns"] == ["shared_match_id"]:
            op.drop_constraint(constraint["name"], "game_engine_sessions", type_="foreignkey")
    for name in ["shared_match_id", "format_key", "match_status", "completion_reason", "wrong_count", "pending_count"]:
        op.drop_column("game_engine_sessions", name)
    op.drop_table("pasapalabra_matches")
