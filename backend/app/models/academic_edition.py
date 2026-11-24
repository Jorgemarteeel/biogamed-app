import uuid

from sqlalchemy import Boolean, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, false, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AcademicEdition(Base):
    __tablename__ = "academic_editions"
    __table_args__ = (
        UniqueConstraint("subject_id", "academic_year", name="uq_edition_subject_year"),
        UniqueConstraint("id", "subject_id", name="uq_edition_id_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"))
    academic_year: Mapped[str] = mapped_column(String(9))


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["edition_id", "subject_id"], ["academic_editions.id", "academic_editions.subject_id"],
            name="fk_enrollment_edition_subject", ondelete="RESTRICT",
        ),
        Index("ix_enrollments_edition_id", "edition_id"),
        Index(
            "uq_enrollment_enabled_subject", "student_id", "subject_id", unique=True,
            postgresql_where=text("play_enabled"), sqlite_where=text("play_enabled"),
        ),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    edition_id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int]
    play_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
