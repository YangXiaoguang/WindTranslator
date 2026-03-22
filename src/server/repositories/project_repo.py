"""Repository for TranslationProject CRUD operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.project import TranslationProject


class ProjectRepository:
    """Data-access layer for TranslationProject."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs: object) -> TranslationProject:
        """Insert a new project and flush to obtain its id."""
        project = TranslationProject(**kwargs)
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_by_id(
        self, project_id: str, *, load_chapters: bool = False
    ) -> Optional[TranslationProject]:
        """Fetch a project by primary key, optionally eager-loading chapters."""
        stmt = select(TranslationProject).where(TranslationProject.id == project_id)
        if load_chapters:
            stmt = stmt.options(selectinload(TranslationProject.chapters))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[TranslationProject]:
        """Return all projects ordered by creation time (newest first)."""
        stmt = (
            select(TranslationProject)
            .order_by(TranslationProject.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self, project_id: str, status: str, **extra: object
    ) -> None:
        """Update a project's status and any additional fields."""
        project = await self.get_by_id(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")
        project.status = status
        for key, value in extra.items():
            setattr(project, key, value)
        await self.session.flush()

    async def delete(self, project_id: str) -> None:
        """Delete a project and cascade to children."""
        project = await self.get_by_id(project_id)
        if project:
            await self.session.delete(project)
            await self.session.flush()
