"""ContentBlock — a paragraph or heading within a chapter."""

from __future__ import annotations

import uuid

from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .chapter import Chapter


class ContentBlock(Base):
    """One content block (heading or paragraph) inside a chapter."""

    __tablename__ = "content_blocks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    chapter_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chapters.id", ondelete="CASCADE")
    )
    index: Mapped[int] = mapped_column(Integer, comment="Order within chapter")
    block_type: Mapped[str] = mapped_column(
        String(10), comment="h1 | h2 | h3 | p"
    )
    text: Mapped[str] = mapped_column(Text, default="", comment="Original text")
    translated: Mapped[str] = mapped_column(Text, default="", comment="Translated text")
    status: Mapped[str] = mapped_column(
        String(20), default="pending",
        comment="pending | translating | completed | failed",
    )

    chapter: Mapped["Chapter"] = relationship(back_populates="blocks")
