from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_blocks.id", ondelete="RESTRICT"), nullable=True, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    block: Mapped["ContentBlock | None"] = relationship(back_populates="categories")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="category", passive_deletes="all",
    )
