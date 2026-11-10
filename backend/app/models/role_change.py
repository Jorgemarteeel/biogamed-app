from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class RoleChange(Base):
    __tablename__ = "user_role_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'),nullable=False)
    target_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'),nullable=False)
    previous_role: Mapped[str] = mapped_column(String(20),nullable=False)
    new_role: Mapped[str] = mapped_column(String(20),nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False)
