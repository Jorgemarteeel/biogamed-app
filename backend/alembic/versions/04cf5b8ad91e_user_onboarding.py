"""Add DNI identity, activation and import receipts."""
from alembic import op
import sqlalchemy as sa


revision = "04cf5b8ad91e"
down_revision = "f3be4a7fc80d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("dni", sa.String(9), nullable=True))
    op.create_unique_constraint("uq_users_dni", "users", ["dni"])
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)
    op.add_column("users", sa.Column("activation_hash", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_users_activation_hash", "users", ["activation_hash"])
    op.add_column("users", sa.Column("activation_expires_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("invitation_attempted_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("invitation_sent_at", sa.DateTime(timezone=True)))
    op.create_table(
        "user_imports",
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("target", sa.String(16), primary_key=True),
        sa.Column("fingerprint", sa.String(64), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT 1 FROM users WHERE dni IS NOT NULL OR hashed_password IS NULL LIMIT 1")):
        raise RuntimeError("User onboarding data exists; restore a verified backup to roll back.")
    op.drop_table("user_imports")
    op.drop_constraint("uq_users_activation_hash", "users", type_="unique")
    for name in ("activation_hash", "activation_expires_at", "invitation_attempted_at", "invitation_sent_at"):
        op.drop_column("users", name)
    op.drop_constraint("uq_users_dni", "users", type_="unique")
    op.drop_column("users", "dni")
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
