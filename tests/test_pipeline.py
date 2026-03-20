import pytest
from unittest.mock import MagicMock, patch
from epub_translator.pipeline import TranslationPipeline, PipelineError
from epub_translator.models import Chapter, ContentBlock
from epub_translator.config import TranslatorConfig


def _make_chapter(title="Ch1", n_blocks=3):
    blocks = [ContentBlock("h1", title)] + [
        ContentBlock("p", f"Para {i}") for i in range(n_blocks - 1)
    ]
    return Chapter(title=title, blocks=blocks)


@pytest.fixture
def mock_deps():
    """Return mocked parser, translator, and renderer for pipeline tests."""
    chapter = _make_chapter()
    parser = MagicMock()
    parser.get_title.return_value = "Test Book"
    parser.get_chapters.return_value = [chapter]

    translator = MagicMock()
    translator.translate_chapter.side_effect = lambda ch: ch

    renderer = MagicMock()
    return parser, translator, renderer, chapter


def _run_pipeline(tmp_path, minimal_cfg, parser, translator, renderer, **kwargs):
    with (
        patch("epub_translator.pipeline.get_parser", return_value=parser),
        patch("epub_translator.pipeline.LLMTranslator", return_value=translator),
        patch("epub_translator.pipeline.PDFRenderer", return_value=renderer),
    ):
        TranslationPipeline().run(
            input_path="book.epub",
            output_path=str(tmp_path / "out.pdf"),
            cfg=minimal_cfg,
            **kwargs,
        )


def test_pipeline_runs_all_stages(tmp_path, mock_deps, minimal_cfg):
    parser, translator, renderer, chapter = mock_deps
    _run_pipeline(tmp_path, minimal_cfg, parser, translator, renderer)

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

    _run_pipeline(tmp_path, minimal_cfg, parser, translator, renderer, chapter_range="2-3")

    translated = [c.args[0] for c in translator.translate_chapter.call_args_list]
    assert translated == [chapters[1], chapters[2]]


def test_pipeline_raises_on_empty_chapters(tmp_path, minimal_cfg):
    parser = MagicMock()
    parser.get_title.return_value = "Empty"
    parser.get_chapters.return_value = []
    translator = MagicMock()
    renderer = MagicMock()

    with pytest.raises(PipelineError, match="未提取到任何章节"):
        _run_pipeline(tmp_path, minimal_cfg, parser, translator, renderer)


def test_pipeline_raises_on_bad_chapter_range(tmp_path, minimal_cfg):
    parser = MagicMock()
    parser.get_title.return_value = "Book"
    parser.get_chapters.return_value = [_make_chapter()]
    translator = MagicMock()
    renderer = MagicMock()

    with pytest.raises(PipelineError):
        _run_pipeline(
            tmp_path, minimal_cfg, parser, translator, renderer, chapter_range="99"
        )


def test_translator_close_called_on_exception(tmp_path, minimal_cfg):
    """close() must be called even when translate_chapter raises."""
    parser = MagicMock()
    parser.get_title.return_value = "Book"
    parser.get_chapters.return_value = [_make_chapter()]
    translator = MagicMock()
    translator.translate_chapter.side_effect = RuntimeError("API down")
    renderer = MagicMock()

    with pytest.raises(RuntimeError, match="API down"):
        _run_pipeline(tmp_path, minimal_cfg, parser, translator, renderer)

    translator.close.assert_called_once()
