"""Immutable initial shared decks; no draws, reservations or discards."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String
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
