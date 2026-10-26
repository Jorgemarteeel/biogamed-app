from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
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

    topic: Mapped["Topic"] = relationship(back_populates="questions")
    answer_logs: Mapped[list["AnswerLog"]] = relationship(back_populates="question")
