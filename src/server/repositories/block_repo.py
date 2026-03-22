"""Repository for ContentBlock CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.content_block import ContentBlock


class BlockRepository:
    """Data-access layer for ContentBlock."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, blocks: list[ContentBlock]) -> None:
        """Add multiple content blocks in one flush."""
        self.session.add_all(blocks)
        await self.session.flush()

    async def get_by_chapter(self, chapter_id: str) -> list[ContentBlock]:
        """Fetch all blocks for a chapter, ordered by index."""
        stmt = (
            select(ContentBlock)
            .where(ContentBlock.chapter_id == chapter_id)
            .order_by(ContentBlock.index)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_by_chapter(self, chapter_id: str) -> list[ContentBlock]:
        """Fetch only blocks that have not yet been translated."""
        stmt = (
            select(ContentBlock)
            .where(
                ContentBlock.chapter_id == chapter_id,
                ContentBlock.status == "pending",
            )
            .order_by(ContentBlock.index)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_translation(
        self, block_id: str, translated: str, status: str = "completed"
    ) -> None:
        """Write the translated text for a single block."""
        block = await self.session.get(ContentBlock, block_id)
        if block is None:
            raise ValueError(f"Block {block_id} not found")
        block.translated = translated
        block.status = status
        await self.session.flush()

    async def bulk_update_translation(
        self, updates: list[tuple[str, str]]
    ) -> None:
        """Batch-update translations: list of (block_id, translated_text)."""
        for block_id, translated_text in updates:
            block = await self.session.get(ContentBlock, block_id)
            if block is not None:
                block.translated = translated_text
                block.status = "completed"
        await self.session.flush()

    async def count_by_status(
        self, project_id: str, status: str
    ) -> int:
        """Count blocks with a given status across all chapters of a project."""
        from ..models.chapter import Chapter

        stmt = (
            select(ContentBlock)
            .join(Chapter)
            .where(
                Chapter.project_id == project_id,
                ContentBlock.status == status,
            )
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
