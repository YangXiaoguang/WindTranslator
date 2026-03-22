"""Tests for TranslationEngine — mock LLM provider, verify DB updates.

All LLM calls are mocked; tests verify:
- Blocks are translated and written to DB
- Batch splitting works correctly
- Fallback to one-by-one on split mismatch
- Already-translated blocks are skipped (interrupt recovery)
- Progress callback is invoked
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from server.translator.engine import TranslationEngine
from server.translator.providers.base import BaseLLMProvider
from server.models.project import TranslationProject
from server.models.chapter import Chapter
from server.models.content_block import ContentBlock
from server.repositories.chapter_repo import ChapterRepository
from server.repositories.block_repo import BlockRepository


class FakeProvider(BaseLLMProvider):
    """A mock LLM provider that returns predictable translations."""

    def __init__(self):
        self.call_count = 0

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Return Chinese text; handle <<<SPLIT>>> batching."""
        self.call_count += 1
        if "<<<SPLIT>>>" in user:
            parts = user.split("<<<SPLIT>>>")
            translated = [f"翻译_{p.strip()}" for p in parts if p.strip()]
            return "\n<<<SPLIT>>>\n".join(translated)
        return f"翻译_{user.strip()}"


async def _seed_project(session, num_paragraphs=3):
    """Insert a project with one chapter and N paragraphs into the DB."""
    project = TranslationProject(
        filename="test.epub",
        file_path="/tmp/test.epub",
        format="epub",
        title="Test Book",
        status="parsed",
    )
    session.add(project)
    await session.flush()

    chapter = Chapter(
        project_id=project.id,
        index=1,
        title="Introduction",
        block_count=num_paragraphs + 1,
        status="pending",
    )
    session.add(chapter)
    await session.flush()

    blocks = [
        ContentBlock(
            chapter_id=chapter.id,
            index=0,
            block_type="h1",
            text="Introduction",
            status="pending",
        )
    ]
    for i in range(num_paragraphs):
        blocks.append(ContentBlock(
            chapter_id=chapter.id,
            index=i + 1,
            block_type="p",
            text=f"Paragraph {i + 1} text here.",
            status="pending",
        ))
    session.add_all(blocks)
    await session.flush()
    await session.commit()

    return project, chapter, blocks


class TestTranslationEngine:
    """Test suite for TranslationEngine."""

    @pytest.mark.asyncio
    async def test_translate_all_blocks(self, session):
        """All blocks should have translated text after translation."""
        project, chapter, blocks = await _seed_project(session, num_paragraphs=2)

        provider = FakeProvider()
        engine = TranslationEngine(
            session=session,
            provider=provider,
            system_prompt="test prompt",
        )
        await engine.translate_project(project.id)

        block_repo = BlockRepository(session)
        updated = await block_repo.get_by_chapter(chapter.id)

        for block in updated:
            assert block.status == "completed"
            assert block.translated.startswith("翻译_")

    @pytest.mark.asyncio
    async def test_heading_translated_separately(self, session):
        """Headings should be translated one-by-one, not batched."""
        project, chapter, _ = await _seed_project(session, num_paragraphs=1)

        provider = FakeProvider()
        engine = TranslationEngine(
            session=session,
            provider=provider,
            system_prompt="test prompt",
        )
        await engine.translate_project(project.id)

        block_repo = BlockRepository(session)
        updated = await block_repo.get_by_chapter(chapter.id)

        h1 = [b for b in updated if b.block_type == "h1"][0]
        assert h1.translated == "翻译_Introduction"

    @pytest.mark.asyncio
    async def test_chapter_status_updated(self, session):
        """Chapter status should be 'completed' after translation."""
        project, chapter, _ = await _seed_project(session, num_paragraphs=1)

        provider = FakeProvider()
        engine = TranslationEngine(
            session=session,
            provider=provider,
            system_prompt="test prompt",
        )
        await engine.translate_project(project.id)

        ch_repo = ChapterRepository(session)
        ch = await ch_repo.get_by_id(chapter.id)
        assert ch.status == "completed"

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, session):
        """The on_progress callback should be invoked during translation."""
        project, _, _ = await _seed_project(session, num_paragraphs=2)

        progress_calls = []
        def on_progress(done, total, title):
            progress_calls.append((done, total, title))

        provider = FakeProvider()
        engine = TranslationEngine(
            session=session,
            provider=provider,
            system_prompt="test prompt",
            on_progress=on_progress,
        )
        await engine.translate_project(project.id)

        assert len(progress_calls) > 0
        last_done, last_total, _ = progress_calls[-1]
        assert last_done == last_total  # all done

    @pytest.mark.asyncio
    async def test_skip_already_translated_blocks(self, session):
        """Blocks already marked 'completed' should be skipped."""
        project, chapter, blocks = await _seed_project(session, num_paragraphs=2)

        # Mark first paragraph as already translated
        blocks[1].status = "completed"
        blocks[1].translated = "已翻译"
        await session.commit()

        provider = FakeProvider()
        engine = TranslationEngine(
            session=session,
            provider=provider,
            system_prompt="test prompt",
        )
        await engine.translate_project(project.id)

        block_repo = BlockRepository(session)
        updated = await block_repo.get_by_chapter(chapter.id)

        # The pre-translated block should keep its old translation
        p1 = [b for b in updated if b.index == 1][0]
        assert p1.translated == "已翻译"

    @pytest.mark.asyncio
    async def test_fallback_on_split_mismatch(self, session):
        """When batch split count doesn't match, fall back to one-by-one."""
        project, chapter, _ = await _seed_project(session, num_paragraphs=2)

        call_idx = 0

        class BadSplitProvider(BaseLLMProvider):
            def complete(self, system, user, max_tokens=4096):
                nonlocal call_idx
                call_idx += 1
                if "<<<SPLIT>>>" in user:
                    # Return wrong number of splits
                    return "只有一段翻译"
                return f"翻译_{user.strip()}"

        engine = TranslationEngine(
            session=session,
            provider=BadSplitProvider(),
            system_prompt="test prompt",
        )
        await engine.translate_project(project.id)

        block_repo = BlockRepository(session)
        updated = await block_repo.get_by_chapter(chapter.id)
        for block in updated:
            assert block.status == "completed"
            assert block.translated != ""

    @pytest.mark.asyncio
    async def test_translate_selected_chapters(self, session):
        """Only specified chapter indices should be translated."""
        project = TranslationProject(
            filename="test.epub", file_path="/tmp/test.epub",
            format="epub", title="Multi", status="parsed",
        )
        session.add(project)
        await session.flush()

        for idx in (1, 2):
            ch = Chapter(
                project_id=project.id, index=idx,
                title=f"Ch {idx}", block_count=1, status="pending",
            )
            session.add(ch)
            await session.flush()
            session.add(ContentBlock(
                chapter_id=ch.id, index=0, block_type="p",
                text=f"Text {idx}", status="pending",
            ))
        await session.commit()

        provider = FakeProvider()
        engine = TranslationEngine(
            session=session, provider=provider, system_prompt="test",
        )
        # Only translate chapter 2
        await engine.translate_project(project.id, chapter_indices=[2])

        ch_repo = ChapterRepository(session)
        chapters = await ch_repo.get_by_project(project.id)
        assert chapters[0].status == "pending"   # ch 1 untouched
        assert chapters[1].status == "completed"  # ch 2 done
