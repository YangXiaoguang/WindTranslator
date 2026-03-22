"""EPUB parser service — parses an EPUB file and persists results to the DB."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.project import TranslationProject
from ..models.chapter import Chapter
from ..models.content_block import ContentBlock
from ..repositories.project_repo import ProjectRepository
from ..repositories.chapter_repo import ChapterRepository
from ..repositories.block_repo import BlockRepository

log = logging.getLogger(__name__)


class EPUBParserService:
    """Parse an EPUB file and write Project/Chapter/Block rows to the DB."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.project_repo = ProjectRepository(session)
        self.chapter_repo = ChapterRepository(session)
        self.block_repo = BlockRepository(session)

    async def parse_and_persist(
        self,
        filepath: str,
        filename: str | None = None,
    ) -> TranslationProject:
        """Parse *filepath* and return a fully-populated TranslationProject.

        All chapters and content blocks are committed inside one transaction.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")

        ext = path.suffix.lower()
        if ext not in (".epub", ".pdf"):
            raise ValueError(f"不支持的格式: {ext}")

        # Use the existing engine parser to extract in-memory objects
        title, raw_chapters = self._extract(filepath, ext)

        # Create the project row
        project = await self.project_repo.create(
            filename=filename or path.name,
            file_path=str(path.resolve()),
            format=ext.lstrip("."),
            title=title,
            status="parsed",
            file_size=path.stat().st_size,
        )

        total_blocks = 0
        for ch_idx, raw_ch in enumerate(raw_chapters, start=1):
            preview = ""
            for b in raw_ch.blocks:
                if b.block_type == "p":
                    preview = b.text[:200]
                    break

            chapter = await self.chapter_repo.create(
                project_id=project.id,
                index=ch_idx,
                title=raw_ch.title,
                block_count=len(raw_ch.blocks),
                preview_text=preview,
                status="pending",
            )

            db_blocks: list[ContentBlock] = []
            for blk_idx, raw_blk in enumerate(raw_ch.blocks):
                db_blocks.append(ContentBlock(
                    chapter_id=chapter.id,
                    index=blk_idx,
                    block_type=raw_blk.block_type,
                    text=raw_blk.text,
                    status="pending",
                ))
            await self.block_repo.bulk_create(db_blocks)
            total_blocks += len(db_blocks)

        # Update project totals
        project.total_chapters = len(raw_chapters)
        project.total_blocks = total_blocks
        await self.session.commit()

        log.info(
            "解析完成: %s — %d 章, %d 块",
            title, len(raw_chapters), total_blocks,
        )
        return project

    @staticmethod
    def _extract(
        filepath: str, ext: str
    ) -> tuple[str, list]:
        """Delegate to the existing engine parsers (sync, no DB)."""
        from epub_translator.parser import get_parser

        parser = get_parser(filepath)
        title = parser.get_title()
        chapters = parser.get_chapters()
        return title, chapters
