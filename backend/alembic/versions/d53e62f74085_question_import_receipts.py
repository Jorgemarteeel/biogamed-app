"""Durable atomic question import receipts."""
from alembic import op
import sqlalchemy as sa
revision = "d53e62f74085"
down_revision = "c42d51e63f74"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("question_import_receipts",
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("operation_id", sa.String(36), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("question_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))

def downgrade():
    raise RuntimeError("Import receipts must be preserved; no automatic downgrade")
