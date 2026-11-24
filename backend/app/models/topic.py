from typing import Optional

from sqlalchemy import String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("edition_id", "name", name="uq_topic_edition_name"),
                      UniqueConstraint("id", "edition_id", name="uq_topic_id_edition"))
    edition_id: Mapped[int | None] = mapped_column(ForeignKey("academic_editions.id", ondelete="RESTRICT"), nullable=True)
    icon_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    questions: Mapped[list["Question"]] = relationship(back_populates="topic", foreign_keys="Question.topic_id")
