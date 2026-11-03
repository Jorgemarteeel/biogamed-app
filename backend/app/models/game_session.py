import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.utils.game_errors import LEGACY_SESSION_NO_SNAPSHOT


class GameSession(Base):
    __tablename__ = "game_engine_sessions"

    user: Mapped["User"] = relationship(back_populates="game_sessions")
    answer_logs: Mapped[list["AnswerLog"]] = relationship(back_populates="game_session", order_by="AnswerLog.id")

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    question_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    content_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Private: contains solutions. Never serialize this column to a player response.
    question_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True, deferred=True)

    game_mode: Mapped[str] = mapped_column(
        String(20), default="TRIVIAL", server_default="TRIVIAL", nullable=False
    )

    @property
    def question_content_source(self) -> str:
        return "session_start" if self.question_snapshot is not None else "legacy"

    @property
    def continuation_error_code(self) -> str | None:
        return LEGACY_SESSION_NO_SNAPSHOT if not self.is_completed and self.question_snapshot is None else None
