"""Translation engine — reads blocks from DB, translates, writes back.

Supports:
- Batch translation with <<<SPLIT>>> separator
- Fallback to one-by-one on split mismatch
- Skip already-translated blocks (interrupt recovery)
- Progress callbacks for WebSocket integration
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.content_block import ContentBlock
from ..repositories.chapter_repo import ChapterRepository
from ..repositories.block_repo import BlockRepository
from .providers.base import BaseLLMProvider

log = logging.getLogger(__name__)

# Type alias for the progress callback
# (blocks_done, blocks_total, chapter_title) → None
ProgressCallback = Callable[[int, int, str], None]

_FALLBACK_SYSTEM_PROMPT = (
    "你是一位专业翻译专家，将英文书籍原文译为简体中文。要求：\n"
    "1. 译文专业、流畅，符合中文表达习惯\n"
    "2. 保持原文语气与段落结构\n"
    "3. 输入段落之间用 <<<SPLIT>>> 分隔，输出必须保持相同数量的段落，"
    "   仍用 <<<SPLIT>>> 分隔，不得增删段落或添加任何说明文字"
)


class TranslationEngine:
    """Orchestrates the translation of all blocks in a project."""

    def __init__(
        self,
        session: AsyncSession,
        provider: BaseLLMProvider,
        system_prompt: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.system_prompt = system_prompt or self._load_system_prompt()
        self.on_progress = on_progress

        settings = get_settings()
        self.batch_char_limit = settings.batch_char_limit
        self.separator = settings.separator

        self._chapter_repo = ChapterRepository(session)
        self._block_repo = BlockRepository(session)

    def _load_system_prompt(self) -> str:
        """Try to load system_prompt.md from cwd or home, else use fallback."""
        candidates = [
            Path.cwd() / "system_prompt.md",
            Path.home() / ".system_prompt.md",
        ]
        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        log.warning("未找到 system_prompt.md，使用内置提示词")
        return _FALLBACK_SYSTEM_PROMPT

    # ── Public API ──────────────────────────────────────────────────────

    async def translate_project(
        self,
        project_id: str,
        chapter_indices: list[int] | None = None,
    ) -> None:
        """Translate all (or selected) chapters of a project.

        Args:
            project_id: The project to translate.
            chapter_indices: 1-based indices to translate. None = all.
        """
        chapters = await self._chapter_repo.get_by_project(
            project_id, load_blocks=True,
        )
        if chapter_indices:
            idx_set = set(chapter_indices)
            chapters = [ch for ch in chapters if ch.index in idx_set]

        # Compute total pending blocks for progress reporting
        total_blocks = sum(
            1 for ch in chapters for b in ch.blocks if b.status == "pending"
        )
        done_blocks = 0

        for chapter in chapters:
            await self._chapter_repo.update_status(chapter.id, "translating")
            pending = [b for b in chapter.blocks if b.status == "pending"]
            done_blocks = await self._translate_blocks(
                pending, chapter.title, done_blocks, total_blocks,
            )
            await self._chapter_repo.update_status(chapter.id, "completed")
            await self.session.commit()

    # ── Internal helpers ────────────────────────────────────────────────

    async def _translate_blocks(
        self,
        blocks: list[ContentBlock],
        chapter_title: str,
        done_so_far: int,
        total: int,
    ) -> int:
        """Translate a list of blocks using batching. Returns updated done count."""
        heading_types = {"h1", "h2", "h3"}
        batch_ids: list[str] = []
        batch_texts: list[str] = []

        async def flush() -> int:
            nonlocal done_so_far
            if not batch_texts:
                return done_so_far
            translations = self._translate_batch(list(batch_texts))
            updates = list(zip(list(batch_ids), translations))
            await self._block_repo.bulk_update_translation(updates)
            done_so_far += len(updates)
            if self.on_progress:
                self.on_progress(done_so_far, total, chapter_title)
            batch_ids.clear()
            batch_texts.clear()
            return done_so_far

        for block in blocks:
            if block.block_type in heading_types:
                done_so_far = await flush()
                translation = self._translate_batch([block.text])[0]
                await self._block_repo.update_translation(block.id, translation)
                done_so_far += 1
                if self.on_progress:
                    self.on_progress(done_so_far, total, chapter_title)
            else:
                batch_ids.append(block.id)
                batch_texts.append(block.text)
                if sum(len(t) for t in batch_texts) >= self.batch_char_limit:
                    done_so_far = await flush()

        done_so_far = await flush()
        return done_so_far

    def _translate_batch(self, texts: list[str]) -> list[str]:
        """Translate texts as one batched LLM call; fall back to one-by-one."""
        if not texts:
            return []
        joined = self.separator.join(texts)
        result = self.provider.complete(self.system_prompt, joined)
        raw_parts = re.split(r"\s*<<<SPLIT>>>\s*", result.strip())
        parts = [p.strip() for p in raw_parts if p.strip()]
        if len(parts) == len(texts):
            return parts
        log.warning(
            "批量分割不符 (期望 %d, 得到 %d)，逐条翻译",
            len(texts), len(parts),
        )
        return [self.provider.complete(self.system_prompt, t) for t in texts]
