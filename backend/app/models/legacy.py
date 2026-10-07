import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class GameMode(str, enum.Enum):
    TRIVIAL = "Trivial"
    PASAPALABRA = "Pasapalabra"


class AnswerStatus(str, enum.Enum):
    CORRECT = "Correct"
    INCORRECT = "Incorrect"
    SKIPPED = "Skipped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.STUDENT,
    )

    game_sessions: Mapped[list["LegacyGameSession"]] = relationship(
        back_populates="user"
    )


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    questions: Mapped[list["Question"]] = relationship(back_populates="topic")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    options: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    correct_option_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    game_letter: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id"), nullable=False
    )

    topic: Mapped["Topic"] = relationship(back_populates="questions")
    answer_logs: Mapped[list["AnswerLog"]] = relationship(
        back_populates="question"
    )


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

