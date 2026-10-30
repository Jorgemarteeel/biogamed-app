from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "difficulty IS NULL OR difficulty BETWEEN 1 AND 4",
            name="ck_question_difficulty",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Source levels from the prototype; their academic meaning is not validated yet.
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    correct_option_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_letter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    question_type: Mapped[str] = mapped_column(
        String(20), default="TRIVIAL", server_default="TRIVIAL", nullable=False
    )
    letter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    exact_word: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accepted_answers: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True,
    )

    topic: Mapped["Topic"] = relationship(back_populates="questions")
    category: Mapped["Category | None"] = relationship(back_populates="questions")
    answer_logs: Mapped[list["AnswerLog"]] = relationship(back_populates="question")
