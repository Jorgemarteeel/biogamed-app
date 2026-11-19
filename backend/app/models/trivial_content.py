"""Private frozen content and immutable versioned presentations."""
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
        UniqueConstraint('match_id','id', name='uq_trivial_presentation_match_id'),
        UniqueConstraint('match_id','request_operation_id', name='uq_trivial_presentation_request'),
        ForeignKeyConstraint(['match_id','copy_id'],['trivial_board_content_copies.match_id','trivial_board_content_copies.id']),
        ForeignKeyConstraint(['match_id','participant_slot'],['trivial_board_participants.match_id','trivial_board_participants.slot']),
        ForeignKeyConstraint(['match_id','turn_number'],['trivial_board_turns.match_id','trivial_board_turns.number']),
        ForeignKeyConstraint(['match_id','arrival_operation_id'],['trivial_board_operations.match_id','trivial_board_operations.operation_id']),
        ForeignKeyConstraint(['match_id','reader_slot'],['trivial_board_participants.match_id','trivial_board_participants.slot'], name='fk_trivial_presentation_reader'),
        ForeignKeyConstraint(['match_id','request_operation_id'],['trivial_board_operations.match_id','trivial_board_operations.operation_id'], name='fk_trivial_presentation_request'),
        CheckConstraint('cell BETWEEN 1 AND 140'),
        CheckConstraint('deadline_at > opened_at'),
        CheckConstraint('(presentation_version = 1 AND deadline_at IS NOT NULL AND reader_slot IS NULL '
                        'AND request_operation_id IS NULL AND deck_cycle IS NULL) OR '
                        '(presentation_version = 2 AND deadline_at IS NULL AND reader_slot IS NOT NULL '
                        'AND reader_slot <> participant_slot AND request_operation_id IS NOT NULL '
                        'AND deck_cycle IS NOT NULL AND deck_cycle >= 1)', name='ck_trivial_presentation_version'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('trivial_board_matches.id'), index=True)
    participant_slot: Mapped[int] = mapped_column(Integer)
    turn_number: Mapped[int] = mapped_column(Integer)
    cell: Mapped[int] = mapped_column(Integer)
    copy_id: Mapped[int] = mapped_column(Integer)
    arrival_operation_id: Mapped[str] = mapped_column(String(36))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    presentation_version: Mapped[int] = mapped_column(Integer, server_default='1')
    reader_slot: Mapped[int | None] = mapped_column(Integer)
    request_operation_id: Mapped[str | None] = mapped_column(String(36))
    deck_cycle: Mapped[int | None] = mapped_column(Integer)
