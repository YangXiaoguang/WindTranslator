"""FastAPI dependency injection functions."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a scoped async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
