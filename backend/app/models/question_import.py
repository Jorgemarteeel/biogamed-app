from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class QuestionImport(Base):
    __tablename__ = "question_import_receipts"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    question_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
