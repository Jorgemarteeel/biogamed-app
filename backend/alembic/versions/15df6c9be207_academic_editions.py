"""Add academic editions and enrollments without backfilling existing data."""

from alembic import op
import sqlalchemy as sa


revision = "15df6c9be207"
down_revision = "04cf5b8ad91e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("subjects", sa.Column("code", sa.String(32), nullable=True))
    op.create_unique_constraint("uq_subject_code", "subjects", ["code"])
    op.create_table(
        "academic_editions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("academic_year", sa.String(9), nullable=False),
        sa.UniqueConstraint("subject_id", "academic_year", name="uq_edition_subject_year"),
        sa.UniqueConstraint("id", "subject_id", name="uq_edition_id_subject"),
    )
    op.create_table(
        "enrollments",
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("edition_id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("play_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(
            ["edition_id", "subject_id"], ["academic_editions.id", "academic_editions.subject_id"],
            name="fk_enrollment_edition_subject", ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_enrollments_edition_id", "enrollments", ["edition_id"])
    op.create_index(
        "uq_enrollment_enabled_subject", "enrollments", ["student_id", "subject_id"],
        unique=True, postgresql_where=sa.text("play_enabled"), sqlite_where=sa.text("play_enabled"),
    )
    op.add_column("user_imports", sa.Column("enrolled", sa.Integer(), nullable=True))
    op.add_column("user_imports", sa.Column("already_enrolled", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT 1 FROM academic_editions LIMIT 1")) is not None:
        raise RuntimeError("Academic editions exist; restore a verified backup to roll back.")
    op.drop_column("user_imports", "already_enrolled")
    op.drop_column("user_imports", "enrolled")
    op.drop_table("enrollments")
    op.drop_table("academic_editions")
    op.drop_constraint("uq_subject_code", "subjects", type_="unique")
    op.drop_column("subjects", "code")
