from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AnswerLog(Base):
    __tablename__ = "answer_logs"
    __table_args__ = (
        UniqueConstraint("game_session_id", "question_id", name="uq_answer_session_question"),
        CheckConstraint("response_time_ms IS NULL OR response_time_ms >= 0", name="ck_answer_response_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_engine_sessions.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    letter: Mapped[str | None] = mapped_column(String(1), nullable=True)
    selected_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_option_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exact_word: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    game_session: Mapped["GameSession"] = relationship(back_populates="answer_logs")
    question: Mapped["Question"] = relationship(back_populates="answer_logs")
