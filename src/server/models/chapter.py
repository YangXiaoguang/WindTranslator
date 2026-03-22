"""Chapter — one chapter extracted from a book."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .project import TranslationProject
    from .content_block import ContentBlock


class Chapter(Base):
    """A single chapter belonging to a TranslationProject."""

    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("translation_projects.id", ondelete="CASCADE")
    )
    index: Mapped[int] = mapped_column(Integer, comment="1-based chapter number")
    title: Mapped[str] = mapped_column(String(500), default="")
    block_count: Mapped[int] = mapped_column(Integer, default=0)
    preview_text: Mapped[str] = mapped_column(Text, default="", comment="First 200 chars")
    status: Mapped[str] = mapped_column(
        String(20), default="pending",
        comment="pending | translating | completed | failed",
    )

    project: Mapped["TranslationProject"] = relationship(back_populates="chapters")
    blocks: Mapped[List["ContentBlock"]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="ContentBlock.index",
    )
