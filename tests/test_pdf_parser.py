"""
Tests for PDFParser.

pdfplumber is mocked throughout so no real PDF file is needed.
The mock surface used by PDFParser:
  - pdfplumber.open(path) → context manager yielding a pdf object
  - pdf.metadata          → dict (may be None)
  - pdf.pages             → list of page objects
  - page.extract_words(extra_attrs, use_text_flow) → list of word dicts
"""

import pytest
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch, call
from epub_translator.parser.pdf import PDFParser, _Line, _HEADING_RATIO


# ── Helpers ────────────────────────────────────────────────────────────────────

def _word(text: str, top: float, size: float, fontname: str = "Times-Roman") -> dict:
    return {"text": text, "top": top, "size": size, "fontname": fontname}


def _make_pdf_mock(pages_words: List[List[Dict]], metadata: Optional[Dict] = None):
    """Build a pdfplumber mock from a list-of-pages, each being a list of words."""
    page_mocks = []
    for words in pages_words:
        page = MagicMock()
        page.extract_words.return_value = words
        page_mocks.append(page)

    pdf_mock = MagicMock()
    pdf_mock.__enter__ = lambda s: pdf_mock
    pdf_mock.__exit__ = MagicMock(return_value=False)
    pdf_mock.metadata = metadata or {}
    pdf_mock.pages = page_mocks
    return pdf_mock


def _make_open(pdf_mock):
    """Patch factory: pdfplumber.open(...) returns pdf_mock."""
    return MagicMock(return_value=pdf_mock)


# ── get_title ──────────────────────────────────────────────────────────────────

class TestGetTitle:
    def test_title_from_metadata(self, tmp_path):
        pdf_mock = _make_pdf_mock([[]], metadata={"Title": "Deep Learning"})
        with patch("epub_translator.parser.pdf._open_pdfplumber") as mock_lib:
            mock_lib.return_value.open = _make_open(pdf_mock)
            parser = PDFParser("book.pdf")
            title = parser.get_title()
        assert title == "Deep Learning"

    def test_falls_back_to_filename_when_no_metadata(self, tmp_path):
        pdf_mock = _make_pdf_mock([[]], metadata=None)
        with patch("epub_translator.parser.pdf._open_pdfplumber") as mock_lib:
            mock_lib.return_value.open = _make_open(pdf_mock)
            parser = PDFParser("/some/path/my_book.pdf")
            title = parser.get_title()
        assert title == "my_book"

    def test_falls_back_to_filename_when_title_blank(self, tmp_path):
        pdf_mock = _make_pdf_mock([[]], metadata={"Title": "   "})
        with patch("epub_translator.parser.pdf._open_pdfplumber") as mock_lib:
            mock_lib.return_value.open = _make_open(pdf_mock)
            parser = PDFParser("/books/deep_learning.pdf")
            title = parser.get_title()
        assert title == "deep_learning"


# ── _classify ──────────────────────────────────────────────────────────────────

class TestClassify:
    """Unit tests for the static font-size classification logic."""

    def test_large_font_becomes_h1(self):
        lines = [
            _Line("Chapter One", size=24.0, bold=False, page=1),
            _Line("Body text here.", size=12.0, bold=False, page=1),
        ]
        result = PDFParser._classify(lines)
        assert result[0][0] == "h1"
        assert result[1][0] == "p"

    def test_two_heading_sizes_map_to_h1_and_h2(self):
        # Need enough body lines so median falls squarely in body range (12pt),
        # otherwise 20pt "Chapter" line could pull the median up.
        lines = [
            _Line("Part I", size=28.0, bold=False, page=1),
            _Line("Chapter One", size=20.0, bold=False, page=1),
            _Line("Body paragraph.", size=12.0, bold=False, page=1),
            _Line("More body text.", size=12.0, bold=False, page=1),
            _Line("Even more body.", size=12.0, bold=False, page=1),
        ]
        # median([28, 20, 12, 12, 12]) = 12 → threshold = 15 → both 28 and 20 qualify
        result = PDFParser._classify(lines)
        types = [r[0] for r in result]
        assert types == ["h1", "h2", "p", "p", "p"]

    def test_bold_text_above_threshold_becomes_h3(self):
        # Body size must be the median, so add enough 12pt lines.
        # With median=12, bold_threshold=13.2; size=14 bold → h3.
        # heading_threshold = 15 so size=14 stays below → not h1/h2.
        lines = [
            _Line("Bold subheading", size=14.0, bold=True, page=1),
            _Line("Regular text one.", size=12.0, bold=False, page=1),
            _Line("Regular text two.", size=12.0, bold=False, page=1),
            _Line("Regular text three.", size=12.0, bold=False, page=1),
        ]
        result = PDFParser._classify(lines)
        assert result[0][0] == "h3"
        assert all(bt == "p" for bt, _ in result[1:])

    def test_empty_lines_returns_empty(self):
        assert PDFParser._classify([]) == []

    def test_uniform_font_sizes_all_become_paragraphs(self):
        lines = [_Line(f"Line {i}", size=12.0, bold=False, page=1) for i in range(5)]
        result = PDFParser._classify(lines)
        assert all(bt == "p" for bt, _ in result)


# ── get_chapters ───────────────────────────────────────────────────────────────

class TestGetChapters:
    def _parse(self, pages_words):
        pdf_mock = _make_pdf_mock(pages_words)
        with patch("epub_translator.parser.pdf._open_pdfplumber") as mock_lib:
            mock_lib.return_value.open = _make_open(pdf_mock)
            parser = PDFParser("book.pdf")
            return parser.get_chapters()

    def test_h1_splits_into_chapters(self):
        words = [
            _word("Chapter One", top=100, size=24),
            _word("First paragraph.", top=120, size=12),
            _word("Chapter Two", top=300, size=24),
            _word("Second paragraph.", top=320, size=12),
        ]
        chapters = self._parse([words])
        assert len(chapters) == 2
        assert chapters[0].title == "Chapter One"
        assert chapters[1].title == "Chapter Two"

    def test_chapter_contains_heading_and_body_blocks(self):
        words = [
            _word("Introduction", top=50, size=24),
            _word("Some body text here.", top=80, size=12),
        ]
        chapters = self._parse([words])
        assert len(chapters) == 1
        types = [b.block_type for b in chapters[0].blocks]
        assert "h1" in types
        assert "p" in types

    def test_no_headings_returns_single_chapter(self):
        words = [
            _word("First sentence here.", top=50, size=12),
            _word("Second sentence here.", top=70, size=12),
        ]
        chapters = self._parse([words])
        assert len(chapters) == 1
        assert len(chapters[0].blocks) >= 1

    def test_empty_pdf_returns_empty_list(self):
        chapters = self._parse([[]])
        assert chapters == []

    def test_words_on_same_line_are_merged(self):
        # Two words at nearly the same top coordinate → same line → one block text
        words = [
            _word("Chapter", top=50.0, size=24),
            _word("One", top=50.5, size=24),   # within tolerance
            _word("Body text here please.", top=80, size=12),
        ]
        chapters = self._parse([words])
        assert len(chapters) == 1
        # First block should contain both words merged
        heading_block = chapters[0].blocks[0]
        assert "Chapter" in heading_block.text
        assert "One" in heading_block.text

    def test_multi_page_chapters(self):
        page1 = [
            _word("Chapter One", top=50, size=24),
            _word("First page body.", top=80, size=12),
        ]
        page2 = [
            _word("More body on page two.", top=50, size=12),
        ]
        chapters = self._parse([page1, page2])
        assert len(chapters) == 1
        # Both body blocks should be present
        body_blocks = [b for b in chapters[0].blocks if b.block_type == "p"]
        assert len(body_blocks) >= 1

    def test_short_text_fragments_skipped(self):
        words = [
            _word("Chapter One", top=50, size=24),
            _word("Hi", top=80, size=12),           # too short (< 3 chars after merge? no, "Hi" = 2)
            _word("Real paragraph text here.", top=100, size=12),
        ]
        chapters = self._parse([words])
        texts = [b.text for b in chapters[0].blocks]
        assert not any(t == "Hi" for t in texts)


# ── get_parser integration ─────────────────────────────────────────────────────

class TestGetParserFactory:
    def test_pdf_extension_returns_pdf_parser(self):
        from epub_translator.parser import get_parser
        p = get_parser("some/path/book.pdf")
        assert isinstance(p, PDFParser)

    def test_epub_extension_returns_epub_parser(self):
        from epub_translator.parser import get_parser
        from epub_translator.parser.epub import EPUBParser
        with patch("epub_translator.parser.epub.epub.read_epub"):
            p = get_parser("some/path/book.epub")
        assert isinstance(p, EPUBParser)

    def test_unsupported_extension_raises(self):
        from epub_translator.parser import get_parser
        with pytest.raises(ValueError, match="不支持的文件格式"):
            get_parser("book.docx")
