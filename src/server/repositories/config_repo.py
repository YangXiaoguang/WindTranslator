"""Repository for TranslationConfig CRUD operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.translation_config import TranslationConfig


class ConfigRepository:
    """Data-access layer for TranslationConfig."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs: object) -> TranslationConfig:
        """Insert a new config and flush."""
        config = TranslationConfig(**kwargs)
        self.session.add(config)
        await self.session.flush()
        return config

    async def get_by_id(self, config_id: str) -> Optional[TranslationConfig]:
        """Fetch a config by primary key."""
        return await self.session.get(TranslationConfig, config_id)

    async def get_default(self) -> Optional[TranslationConfig]:
        """Return the config marked as default, if any."""
        stmt = select(TranslationConfig).where(TranslationConfig.is_default.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[TranslationConfig]:
        """Return all configs ordered by creation time."""
        stmt = select(TranslationConfig).order_by(TranslationConfig.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, config_id: str) -> None:
        """Delete a config by id."""
        config = await self.get_by_id(config_id)
        if config:
            await self.session.delete(config)
            await self.session.flush()
