import pytest
from unittest.mock import MagicMock, patch
from epub_translator.pipeline import TranslationPipeline
from epub_translator.models import Chapter, ContentBlock
from epub_translator.config import TranslatorConfig


def _make_chapter(title="Ch1", n_blocks=3):
    blocks = [ContentBlock("h1", title)] + [
        ContentBlock("p", f"Para {i}") for i in range(n_blocks - 1)
    ]
    return Chapter(title=title, blocks=blocks)


@pytest.fixture
def mock_deps(tmp_path):
    """Return mocked parser, translator, and renderer for pipeline tests."""
    chapter = _make_chapter()
    parser = MagicMock()
    parser.get_title.return_value = "Test Book"
    parser.get_chapters.return_value = [chapter]

    translator = MagicMock()
    translator.translate_chapter.side_effect = lambda ch: ch

    renderer = MagicMock()

    return parser, translator, renderer, chapter


def test_pipeline_runs_all_stages(tmp_path, mock_deps, minimal_cfg):
    parser, translator, renderer, chapter = mock_deps

    with (
        patch("epub_translator.pipeline.EPUBParser", return_value=parser),
        patch("epub_translator.pipeline.LLMTranslator", return_value=translator),
        patch("epub_translator.pipeline.PDFRenderer", return_value=renderer),
    ):
        TranslationPipeline().run(
            epub_path="book.epub",
            output_path=str(tmp_path / "out.pdf"),
            cfg=minimal_cfg,
        )

    parser.get_chapters.assert_called_once()
    translator.translate_chapter.assert_called_once_with(chapter)
    renderer.render.assert_called_once()


def test_pipeline_chapter_range_filters(tmp_path, minimal_cfg):
    chapters = [_make_chapter(f"Ch{i}") for i in range(5)]
    parser = MagicMock()
    parser.get_title.return_value = "Book"
    parser.get_chapters.return_value = chapters

    translator = MagicMock()
    translator.translate_chapter.side_effect = lambda ch: ch
    renderer = MagicMock()

    with (
        patch("epub_translator.pipeline.EPUBParser", return_value=parser),
        patch("epub_translator.pipeline.LLMTranslator", return_value=translator),
        patch("epub_translator.pipeline.PDFRenderer", return_value=renderer),
    ):
        TranslationPipeline().run(
            epub_path="book.epub",
            output_path=str(tmp_path / "out.pdf"),
            cfg=minimal_cfg,
            chapter_range="2-3",
        )

    translated = [
        call.args[0] for call in translator.translate_chapter.call_args_list
    ]
    assert translated == [chapters[1], chapters[2]]
