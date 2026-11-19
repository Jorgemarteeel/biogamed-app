"""Private frozen content and immutable arrivals. No answer/result records."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TrivialContentCopy(Base):
    __tablename__ = 'trivial_board_content_copies'
    __table_args__ = (
        UniqueConstraint('match_id','bank','question_id'),
        UniqueConstraint('match_id','id'),
        CheckConstraint("(snapshot_version = 1 AND bank IN ('LYMPHOCYTE','MACROPHAGE','FLASK','SYRINGE')) OR "
                        "(snapshot_version = 2 AND bank IN ('LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA') "
                        "AND difficulty IS NOT NULL AND difficulty BETWEEN 1 AND 4)",
                        name='ck_trivial_copy_format_version'),
        CheckConstraint('difficulty IS NULL OR difficulty BETWEEN 1 AND 4'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('trivial_board_matches.id'), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'))
    bank: Mapped[str] = mapped_column(String(16))
    difficulty: Mapped[int | None] = mapped_column(Integer)
    snapshot_version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON, deferred=True)
    classification: Mapped[dict] = mapped_column(JSON, deferred=True)
    binding_snapshot: Mapped[dict] = mapped_column(JSON, deferred=True)
    copied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TrivialPresentation(Base):
    __tablename__ = 'trivial_board_presentations'
    __table_args__ = (
        UniqueConstraint('match_id','arrival_operation_id'),
        ForeignKeyConstraint(['match_id','copy_id'],['trivial_board_content_copies.match_id','trivial_board_content_copies.id']),
        ForeignKeyConstraint(['match_id','participant_slot'],['trivial_board_participants.match_id','trivial_board_participants.slot']),
        ForeignKeyConstraint(['match_id','turn_number'],['trivial_board_turns.match_id','trivial_board_turns.number']),
        ForeignKeyConstraint(['match_id','arrival_operation_id'],['trivial_board_operations.match_id','trivial_board_operations.operation_id']),
        CheckConstraint('cell BETWEEN 1 AND 140'),
        CheckConstraint('deadline_at > opened_at'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('trivial_board_matches.id'), index=True)
    participant_slot: Mapped[int] = mapped_column(Integer)
    turn_number: Mapped[int] = mapped_column(Integer)
    cell: Mapped[int] = mapped_column(Integer)
    copy_id: Mapped[int] = mapped_column(Integer)
    arrival_operation_id: Mapped[str] = mapped_column(String(36))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
