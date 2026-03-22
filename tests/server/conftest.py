"""Shared fixtures for server tests — in-memory async SQLite database."""

from __future__ import annotations

import pytest
import asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from server.database import Base
from server.models import (  # noqa: F401 — ensure all models register
    TranslationProject,
    Chapter,
    ContentBlock,
    TranslationConfig,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """Create a fresh in-memory SQLite engine per test."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(async_engine):
    """Yield an AsyncSession bound to the in-memory engine."""
    factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with factory() as sess:
        yield sess
