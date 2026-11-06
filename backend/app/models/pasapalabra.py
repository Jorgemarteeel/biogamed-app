"""Persistent shared match state. Question snapshots are private and immutable."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PasapalabraMatch(Base):
    __tablename__ = "pasapalabra_matches"
    __table_args__ = (UniqueConstraint("owner_id", "start_operation_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    start_operation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    start_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    play_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="LOCAL")
    rules_version: Mapped[str] = mapped_column(String(40), nullable=False, default="pasapalabra-local-v1")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="RUNNING")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active_position: Mapped[int | None] = mapped_column(Integer)
    turn_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(16))
    winner_position: Mapped[int | None] = mapped_column(Integer)
    participants: Mapped[list["MatchParticipant"]] = relationship(order_by="MatchParticipant.position")


class MatchParticipant(Base):
    __tablename__ = "pasapalabra_participants"
    __table_args__ = (
        UniqueConstraint("match_id", "position"),
        UniqueConstraint("match_id", "user_id"),
        CheckConstraint("position IN (1, 2)"),
        CheckConstraint("remaining_ms >= 0 AND remaining_ms <= 600000"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("pasapalabra_matches.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("game_engine_sessions.id"), unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PLAYING")
    finish_reason: Mapped[str | None] = mapped_column(String(24))
    remaining_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=600000)
    cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    questions: Mapped[list["MatchQuestion"]] = relationship(order_by="MatchQuestion.number")


class MatchQuestion(Base):
    __tablename__ = "pasapalabra_questions"
    __table_args__ = (
        UniqueConstraint("match_id", "question_id"),
        UniqueConstraint("participant_id", "number"),
        CheckConstraint("number BETWEEN 1 AND 20"),
        CheckConstraint("state IN ('PENDING','PASSED','CORRECT','WRONG')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("pasapalabra_matches.id"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("pasapalabra_participants.id"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    text_answer: Mapped[str | None] = mapped_column(Text)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MatchCommand(Base):
    __tablename__ = "pasapalabra_commands"
    __table_args__ = (UniqueConstraint("match_id", "operation_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("pasapalabra_matches.id"), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)


class PasapalabraRoom(Base):
    __tablename__ = "pasapalabra_rooms"
    __table_args__ = (CheckConstraint("guest_id IS NULL OR guest_id <> owner_id", name="ck_room_distinct_accounts"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    guest_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    selection: Mapped[dict] = mapped_column(JSON, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="WAITING")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    owner_ready: Mapped[bool] = mapped_column(default=False, nullable=False)
    guest_ready: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("pasapalabra_matches.id"), unique=True)


class RoomOperation(Base):
    __tablename__ = "pasapalabra_room_operations"
    __table_args__ = (UniqueConstraint("user_id", "operation_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("pasapalabra_rooms.id"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class RoomJoinLimit(Base):
    __tablename__ = "pasapalabra_join_limits"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
