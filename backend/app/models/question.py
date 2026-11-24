from sqlalchemy import Boolean, CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        ForeignKeyConstraint(["topic_id", "edition_id"], ["topics.id", "topics.edition_id"], name="fk_question_topic_edition", ondelete="RESTRICT"),
        CheckConstraint(
            "difficulty IS NULL OR difficulty BETWEEN 1 AND 4",
            name="ck_question_difficulty",
        ),
    )

    edition_id: Mapped[int | None] = mapped_column(ForeignKey("academic_editions.id", ondelete="RESTRICT"), nullable=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Source levels from the prototype; their academic meaning is not validated yet.
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct_answer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    correct_option_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_letter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    question_type: Mapped[str] = mapped_column(
        String(20), default="TRIVIAL", server_default="TRIVIAL", nullable=False
    )
    letter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    exact_word: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accepted_answers: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=True, index=True)
    block_id: Mapped[int | None] = mapped_column(ForeignKey("content_blocks.id", ondelete="RESTRICT"), nullable=True, index=True)
    subject: Mapped["Subject | None"] = relationship()
    block: Mapped["ContentBlock | None"] = relationship()

    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True,
    )

    topic: Mapped["Topic"] = relationship(back_populates="questions", foreign_keys=[topic_id])
    category: Mapped["Category | None"] = relationship(back_populates="questions")
    answer_logs: Mapped[list["AnswerLog"]] = relationship(back_populates="question")
