"""Async SQLAlchemy engine, session factory, and declarative Base."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import get_settings


log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


_settings = get_settings()

_is_sqlite = "sqlite" in _settings.database_url


def _build_engine():
    """Create the async engine with backend-appropriate settings."""
    if _is_sqlite:
        # SQLite: disable connection pooling to avoid cross-thread issues,
        # and set a generous busy timeout for concurrent access.
        return create_async_engine(
            _settings.database_url,
            echo=False,
            future=True,
            poolclass=NullPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
            },
        )
    # PostgreSQL / other async databases
    return create_async_engine(
        _settings.database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


engine = _build_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a scoped async session for use in FastAPI dependencies."""
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Create all tables and configure database pragmas."""
    async with engine.begin() as conn:
        if _is_sqlite:
            # Enable WAL for concurrent read/write and set busy timeout
            await conn.execute(
                __import__("sqlalchemy").text("PRAGMA journal_mode=WAL")
            )
            await conn.execute(
                __import__("sqlalchemy").text("PRAGMA busy_timeout=5000")
            )
            # Enable foreign key enforcement (off by default in SQLite)
            await conn.execute(
                __import__("sqlalchemy").text("PRAGMA foreign_keys=ON")
            )
            log.info("SQLite: WAL 模式已启用, foreign_keys=ON")

        await conn.run_sync(Base.metadata.create_all)
