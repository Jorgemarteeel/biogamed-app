from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ContentBlock(Base):
    __tablename__ = "content_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    subject: Mapped["Subject"] = relationship(back_populates="blocks")
    categories: Mapped[list["Category"]] = relationship(
        back_populates="block", passive_deletes="all",
    )
