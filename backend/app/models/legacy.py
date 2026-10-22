"""Mappings for the original game tables retained for schema compatibility.

The current game service uses GameSession in game_session.py. Keep these
mappings until historical data and their removal have been handled by a migration.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GameMode(str, enum.Enum):
    TRIVIAL = "Trivial"
    PASAPALABRA = "Pasapalabra"


class AnswerStatus(str, enum.Enum):
    CORRECT = "Correct"
    INCORRECT = "Incorrect"
    SKIPPED = "Skipped"


class LegacyGameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    game_mode: Mapped[GameMode] = mapped_column(
        Enum(GameMode, name="game_mode"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    final_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="game_sessions")
    answer_logs: Mapped[list["AnswerLog"]] = relationship(
        back_populates="game_session"
    )


class AnswerLog(Base):
    __tablename__ = "answer_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("game_sessions.id"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"), nullable=False
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AnswerStatus] = mapped_column(
        Enum(AnswerStatus, name="answer_status"), nullable=False
    )
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    game_session: Mapped["LegacyGameSession"] = relationship(
        back_populates="answer_logs"
    )
    question: Mapped["Question"] = relationship(back_populates="answer_logs")
