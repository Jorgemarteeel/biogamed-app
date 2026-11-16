"""Internal partial Trivial persistence; deliberately unrelated to GameSession."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TrivialBoardMatch(Base):
    __tablename__ = 'trivial_board_matches'
    __table_args__ = (
        UniqueConstraint('owner_id', 'setup_operation_id'),
        CheckConstraint("play_mode IN ('LOCAL','ONLINE')"),
        CheckConstraint('version >= 1 AND current_turn >= 1'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), index=True)
    setup_operation_id: Mapped[str] = mapped_column(String(36))
    setup_payload: Mapped[dict] = mapped_column(JSON)
    play_mode: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer)
    current_turn: Mapped[int] = mapped_column(Integer)
    board_version: Mapped[str] = mapped_column(String(40))
    rules_version: Mapped[str] = mapped_column(String(40))
    state_schema_version: Mapped[int] = mapped_column(Integer)
    board_snapshot: Mapped[dict] = mapped_column(JSON)
    configuration: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TrivialBoardParticipant(Base):
    __tablename__ = 'trivial_board_participants'
    __table_args__ = (
        UniqueConstraint('match_id', 'user_id'),
        CheckConstraint('slot BETWEEN 1 AND 4 AND position BETWEEN 1 AND 140'),
        CheckConstraint("phase IN ('READY','QUESTION_REQUIRED','RULE_PENDING','TURN_ENDED','GOAL_REACHED')"),
        CheckConstraint("NOT skip_next_own_turn OR phase = 'TURN_ENDED'"),
    )
    match_id: Mapped[int] = mapped_column(ForeignKey('trivial_board_matches.id'), primary_key=True)
    slot: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(24))
    skip_next_own_turn: Mapped[bool] = mapped_column(Boolean)


class TrivialBoardTurn(Base):
    __tablename__ = 'trivial_board_turns'
    __table_args__ = (
        ForeignKeyConstraint(['match_id', 'participant_slot'], ['trivial_board_participants.match_id', 'trivial_board_participants.slot']),
        CheckConstraint('number >= 1'),
        CheckConstraint("status IN ('OPEN','ENDED','SKIPPED')"),
    )
    match_id: Mapped[int] = mapped_column(ForeignKey('trivial_board_matches.id'), primary_key=True)
    number: Mapped[int] = mapped_column(primary_key=True)
    participant_slot: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(String(24))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TrivialBoardOperation(Base):
    __tablename__ = 'trivial_board_operations'
    __table_args__ = (
        ForeignKeyConstraint(['match_id', 'participant_slot'], ['trivial_board_participants.match_id', 'trivial_board_participants.slot']),
    )
    match_id: Mapped[int] = mapped_column(ForeignKey('trivial_board_matches.id'), primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    participant_slot: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
