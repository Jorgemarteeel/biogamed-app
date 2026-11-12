"""Credential version for revoking access tokens without rewriting hashes."""
from alembic import op
import sqlalchemy as sa
revision = "e64f73085196"
down_revision = "d53e62f74085"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))

def downgrade():
    raise RuntimeError("Removing credential versions could revive revoked tokens")
