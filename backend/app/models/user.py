import enum
import uuid

from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("dni", name="uq_users_dni"),
                      UniqueConstraint("activation_hash", name="uq_users_activation_hash"))

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dni: Mapped[str | None] = mapped_column(String(9), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activation_hash: Mapped[str | None] = mapped_column(String(64))
    activation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invitation_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invitation_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.STUDENT,
    )

    game_sessions: Mapped[list["GameSession"]] = relationship(
        back_populates="user"
    )
