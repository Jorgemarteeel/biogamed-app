"""Immutable initial decks, canonical circulation and immutable human verdicts."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class InmunoQuestDeck(Base):
    __tablename__ = 'inmunoquest_decks'
    __table_args__ = (
        CheckConstraint("bank IN ('LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA')"),
        CheckConstraint('difficulty BETWEEN 1 AND 4'),
        CheckConstraint('length(shuffle_version) > 0'),
    )
    match_id: Mapped[int] = mapped_column(ForeignKey('trivial_board_matches.id'), primary_key=True)
    bank: Mapped[str] = mapped_column(String(16), primary_key=True)
    difficulty: Mapped[int] = mapped_column(Integer, primary_key=True)
    shuffle_version: Mapped[str] = mapped_column(String(40))
    initial_order: Mapped[list[int]] = mapped_column(JSON, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InmunoQuestDeckState(Base):
    """One canonical circulation partition per immutable shared deck."""
    __tablename__ = 'inmunoquest_deck_states'
    __table_args__ = (
        ForeignKeyConstraint(['match_id', 'bank', 'difficulty'],
                             ['inmunoquest_decks.match_id', 'inmunoquest_decks.bank', 'inmunoquest_decks.difficulty']),
        ForeignKeyConstraint(['match_id', 'reserved_presentation_id'],
                             ['trivial_board_presentations.match_id', 'trivial_board_presentations.id']),
        UniqueConstraint('match_id', 'reserved_presentation_id'),
        CheckConstraint('cycle >= 1'),
    )
    match_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank: Mapped[str] = mapped_column(String(16), primary_key=True)
    difficulty: Mapped[int] = mapped_column(Integer, primary_key=True)
    circulation_version: Mapped[str] = mapped_column(String(40))
    cycle: Mapped[int] = mapped_column(Integer)
    available_order: Mapped[list[int]] = mapped_column(JSON)
    discard_order: Mapped[list[int]] = mapped_column(JSON)
    reserved_presentation_id: Mapped[int | None] = mapped_column(Integer)


class InmunoQuestEvaluation(Base):
    """One immutable human verdict per educational presentation, no transcript."""
    __tablename__ = 'inmunoquest_evaluations'
    __table_args__ = (
        ForeignKeyConstraint(['match_id', 'presentation_id'],
                             ['trivial_board_presentations.match_id', 'trivial_board_presentations.id']),
        ForeignKeyConstraint(['match_id', 'evaluator_slot'],
                             ['trivial_board_participants.match_id', 'trivial_board_participants.slot']),
        ForeignKeyConstraint(['match_id', 'operation_id'],
                             ['trivial_board_operations.match_id', 'trivial_board_operations.operation_id']),
        UniqueConstraint('match_id', 'operation_id'),
    )
    match_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presentation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluator_slot: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    operation_id: Mapped[str] = mapped_column(String(36))
    correct: Mapped[bool] = mapped_column(Boolean)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
