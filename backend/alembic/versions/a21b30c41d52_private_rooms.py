"""Private online rooms and durable room idempotency/rate limits."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "a21b30c41d52"
down_revision = "f17a20b30c41"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("pasapalabra_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("guest_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("code", sa.String(12), unique=True, nullable=False),
        sa.Column("selection", sa.JSON(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("owner_ready", sa.Boolean(), nullable=False),
        sa.Column("guest_ready", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("pasapalabra_matches.id"), unique=True),
        sa.CheckConstraint("guest_id IS NULL OR guest_id <> owner_id", name="ck_room_distinct_accounts"))
    op.create_index("ix_pasapalabra_rooms_owner_id", "pasapalabra_rooms", ["owner_id"])
    op.create_table("pasapalabra_room_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("pasapalabra_rooms.id"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False), sa.UniqueConstraint("user_id", "operation_id"))
    op.create_table("pasapalabra_join_limits",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False))


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM pasapalabra_rooms")):
        raise RuntimeError("Cannot discard private room history.")
    op.drop_table("pasapalabra_join_limits")
    op.drop_table("pasapalabra_room_operations")
    op.drop_table("pasapalabra_rooms")
