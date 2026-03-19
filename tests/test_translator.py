import pytest
from unittest.mock import MagicMock, patch
from epub_translator.models import ContentBlock, Chapter
from epub_translator.translator.llm import LLMTranslator
from epub_translator.config import SEPARATOR


def _make_translator(cfg, provider_mock):
    """Build an LLMTranslator with the provider replaced by a mock."""
    with patch("epub_translator.translator.llm.get_provider", return_value=provider_mock):
        t = LLMTranslator(cfg)
    return t


class TestTranslateChapter:
    def test_headings_translated_individually(self, minimal_cfg, sample_chapter):
        provider = MagicMock()
        provider.complete.side_effect = lambda system, user, **kw: f"[译]{user}"
        t = _make_translator(minimal_cfg, provider)

        t.translate_chapter(sample_chapter)

        h1 = sample_chapter.blocks[0]
        assert h1.translated == "[译]Introduction"

    def test_paragraphs_translated_in_batch(self, minimal_cfg):
        chapter = Chapter(
            title="Ch",
            blocks=[
                ContentBlock("p", "Hello"),
                ContentBlock("p", "World"),
            ],
        )
        provider = MagicMock()
        # Simulate a valid batched response using the real separator format
        provider.complete.return_value = SEPARATOR.join(["你好", "世界"])
        t = _make_translator(minimal_cfg, provider)

        t.translate_chapter(chapter)

        assert chapter.blocks[0].translated == "你好"
        assert chapter.blocks[1].translated == "世界"

    def test_fallback_on_split_count_mismatch(self, minimal_cfg):
        chapter = Chapter(
            title="Ch",
            blocks=[
                ContentBlock("p", "A"),
                ContentBlock("p", "B"),
            ],
        )
        provider = MagicMock()
        # First call returns wrong count; subsequent calls return individual translations
        provider.complete.side_effect = [
            "only one part",   # batch call → mismatch
            "[A]",             # individual fallback for A
            "[B]",             # individual fallback for B
        ]
        t = _make_translator(minimal_cfg, provider)
        t.translate_chapter(chapter)

        assert chapter.blocks[0].translated == "[A]"
        assert chapter.blocks[1].translated == "[B]"

    def test_cache_prevents_duplicate_api_calls(self, minimal_cfg, tmp_path):
        minimal_cfg.cache_enabled = True
        minimal_cfg.cache_db = tmp_path / "cache.db"

        provider = MagicMock()
        provider.complete.return_value = "译文"

        chapter = Chapter("Ch", [ContentBlock("p", "Same text")])
        t = _make_translator(minimal_cfg, provider)
        t.translate_chapter(chapter)

        # Reset block and translate again — should hit cache
        chapter.blocks[0].translated = ""
        t.translate_chapter(chapter)

        assert provider.complete.call_count == 1
        assert chapter.blocks[0].translated == "译文"
        t.close()
