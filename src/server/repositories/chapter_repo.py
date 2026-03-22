"""Repository for Chapter CRUD operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.chapter import Chapter


class ChapterRepository:
    """Data-access layer for Chapter."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs: object) -> Chapter:
        """Insert a new chapter and flush."""
        chapter = Chapter(**kwargs)
        self.session.add(chapter)
        await self.session.flush()
        return chapter

    async def bulk_create(self, chapters: list[Chapter]) -> None:
        """Add multiple chapters in one flush."""
        self.session.add_all(chapters)
        await self.session.flush()

    async def get_by_id(
        self, chapter_id: str, *, load_blocks: bool = False
    ) -> Optional[Chapter]:
        """Fetch a chapter by id, optionally eager-loading blocks."""
        stmt = select(Chapter).where(Chapter.id == chapter_id)
        if load_blocks:
            stmt = stmt.options(selectinload(Chapter.blocks))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_project(
        self, project_id: str, *, load_blocks: bool = False
    ) -> list[Chapter]:
        """Fetch all chapters for a project, ordered by index."""
        stmt = (
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.index)
        )
        if load_blocks:
            stmt = stmt.options(selectinload(Chapter.blocks))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, chapter_id: str, status: str) -> None:
        """Update a chapter's status."""
        chapter = await self.get_by_id(chapter_id)
        if chapter is None:
            raise ValueError(f"Chapter {chapter_id} not found")
        chapter.status = status
        await self.session.flush()
