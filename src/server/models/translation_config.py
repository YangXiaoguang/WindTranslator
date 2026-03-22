"""TranslationConfig — user-saved LLM provider configuration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class TranslationConfig(Base):
    """A named LLM provider configuration with encrypted API key."""

    __tablename__ = "translation_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), comment="User-friendly name")
    provider: Mapped[str] = mapped_column(
        String(20), comment="anthropic | openai | deepseek | custom"
    )
    model: Mapped[str] = mapped_column(String(100))
    api_key_encrypted: Mapped[str] = mapped_column(
        Text, comment="Fernet-encrypted API key"
    )
    base_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Custom OpenAI-compatible endpoint"
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
