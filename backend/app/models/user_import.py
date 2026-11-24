import uuid

from sqlalchemy import Integer, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserImport(Base):
    __tablename__ = "user_imports"

    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    target: Mapped[str] = mapped_column(String(16), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    enrolled: Mapped[int | None]
    already_enrolled: Mapped[int | None]
