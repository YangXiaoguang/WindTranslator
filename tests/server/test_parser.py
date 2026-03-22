"""Tests for EPUBParserService — EPUB parsing and DB persistence.

The underlying epub_translator.parser is mocked so no real file is needed.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from server.parser.epub import EPUBParserService
from server.repositories.project_repo import ProjectRepository
from server.repositories.chapter_repo import ChapterRepository
from server.repositories.block_repo import BlockRepository

# Re-use the engine's in-memory models for mock data
from epub_translator.models import Chapter as EngineChapter
from epub_translator.models import ContentBlock as EngineBlock


def _mock_chapters():
    """Return a list of engine-level Chapter objects for testing."""
    return [
        EngineChapter(
            title="Introduction",
            blocks=[
                EngineBlock(block_type="h1", text="Introduction"),
                EngineBlock(block_type="p", text="This is the first paragraph of the introduction."),
                EngineBlock(block_type="p", text="Second paragraph here."),
            ],
        ),
        EngineChapter(
            title="Chapter One",
            blocks=[
                EngineBlock(block_type="h1", text="Chapter One"),
                EngineBlock(block_type="p", text="Body of chapter one."),
            ],
        ),
    ]


@pytest.fixture
def mock_epub_file(tmp_path):
    """Create a fake .epub file so the file-existence check passes."""
    p = tmp_path / "test_book.epub"
    p.write_bytes(b"PK\x03\x04fake epub content")
    return str(p)


class TestEPUBParserService:
    """Test suite for EPUBParserService.parse_and_persist."""

    @pytest.mark.asyncio
    async def test_parse_creates_project(self, session, mock_epub_file):
        """Parsing an EPUB creates a TranslationProject row."""
        with patch.object(
            EPUBParserService, "_extract", return_value=("Test Book", _mock_chapters())
        ):
            svc = EPUBParserService(session)
            project = await svc.parse_and_persist(mock_epub_file)

        assert project.title == "Test Book"
        assert project.status == "parsed"
        assert project.format == "epub"
        assert project.total_chapters == 2
        assert project.total_blocks == 5  # 3 + 2

    @pytest.mark.asyncio
    async def test_parse_creates_chapters(self, session, mock_epub_file):
        """Parsing creates correct Chapter rows with indices."""
        with patch.object(
            EPUBParserService, "_extract", return_value=("Test Book", _mock_chapters())
        ):
            svc = EPUBParserService(session)
            project = await svc.parse_and_persist(mock_epub_file)

        repo = ChapterRepository(session)
        chapters = await repo.get_by_project(project.id)

        assert len(chapters) == 2
        assert chapters[0].index == 1
        assert chapters[0].title == "Introduction"
        assert chapters[1].index == 2
        assert chapters[1].title == "Chapter One"

    @pytest.mark.asyncio
    async def test_parse_creates_content_blocks(self, session, mock_epub_file):
        """Parsing creates ContentBlock rows with correct types and text."""
        with patch.object(
            EPUBParserService, "_extract", return_value=("Test Book", _mock_chapters())
        ):
            svc = EPUBParserService(session)
            project = await svc.parse_and_persist(mock_epub_file)

        repo = ChapterRepository(session)
        chapters = await repo.get_by_project(project.id)
        block_repo = BlockRepository(session)

        ch1_blocks = await block_repo.get_by_chapter(chapters[0].id)
        assert len(ch1_blocks) == 3
        assert ch1_blocks[0].block_type == "h1"
        assert ch1_blocks[1].block_type == "p"
        assert ch1_blocks[1].text == "This is the first paragraph of the introduction."
        assert all(b.status == "pending" for b in ch1_blocks)

    @pytest.mark.asyncio
    async def test_parse_sets_preview_text(self, session, mock_epub_file):
        """Chapter.preview_text is set to the first paragraph's text."""
        with patch.object(
            EPUBParserService, "_extract", return_value=("Test Book", _mock_chapters())
        ):
            svc = EPUBParserService(session)
            project = await svc.parse_and_persist(mock_epub_file)

        repo = ChapterRepository(session)
        chapters = await repo.get_by_project(project.id)
        assert chapters[0].preview_text == "This is the first paragraph of the introduction."

    @pytest.mark.asyncio
    async def test_parse_file_not_found_raises(self, session):
        """Parsing a non-existent file raises FileNotFoundError."""
        svc = EPUBParserService(session)
        with pytest.raises(FileNotFoundError):
            await svc.parse_and_persist("/nonexistent/book.epub")

    @pytest.mark.asyncio
    async def test_parse_unsupported_format_raises(self, session, tmp_path):
        """Parsing an unsupported format raises ValueError."""
        docx = tmp_path / "book.docx"
        docx.write_bytes(b"fake")
        svc = EPUBParserService(session)
        with pytest.raises(ValueError, match="不支持的格式"):
            await svc.parse_and_persist(str(docx))

    @pytest.mark.asyncio
    async def test_parse_empty_book(self, session, mock_epub_file):
        """Parsing a book with no chapters creates a project with zero counts."""
        with patch.object(
            EPUBParserService, "_extract", return_value=("Empty", [])
        ):
            svc = EPUBParserService(session)
            project = await svc.parse_and_persist(mock_epub_file)

        assert project.total_chapters == 0
        assert project.total_blocks == 0
        assert project.status == "parsed"

    @pytest.mark.asyncio
    async def test_project_repo_list(self, session, mock_epub_file):
        """ProjectRepository.list_all returns persisted projects."""
        with patch.object(
            EPUBParserService, "_extract", return_value=("Book A", _mock_chapters())
        ):
            svc = EPUBParserService(session)
            await svc.parse_and_persist(mock_epub_file)

        repo = ProjectRepository(session)
        projects = await repo.list_all()
        assert len(projects) == 1
        assert projects[0].title == "Book A"
