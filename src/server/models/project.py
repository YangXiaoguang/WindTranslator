"""TranslationProject — top-level entity representing an uploaded book."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .chapter import Chapter


class TranslationProject(Base):
    """An uploaded ebook and its translation state."""

    __tablename__ = "translation_projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(255), comment="Original upload name")
    file_path: Mapped[str] = mapped_column(Text, comment="Server-side storage path")
    format: Mapped[str] = mapped_column(String(10), comment="epub | pdf")
    title: Mapped[str] = mapped_column(String(500), default="")
    total_chapters: Mapped[int] = mapped_column(Integer, default=0)
    total_blocks: Mapped[int] = mapped_column(Integer, default=0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending | parsed | error"
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Celery AsyncResult ID"
    )
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chapters: Mapped[List["Chapter"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Chapter.index",
    )
