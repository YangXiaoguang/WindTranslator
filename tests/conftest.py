import pytest
from epub_translator.models import ContentBlock, Chapter
from epub_translator.config import TranslatorConfig


@pytest.fixture
def sample_chapter():
    return Chapter(
        title="Introduction",
        blocks=[
            ContentBlock("h1", "Introduction"),
            ContentBlock("p", "This is the first paragraph."),
            ContentBlock("p", "This is the second paragraph."),
            ContentBlock("h2", "Background"),
            ContentBlock("p", "Some background text here."),
        ],
    )


@pytest.fixture
def minimal_cfg(tmp_path):
    return TranslatorConfig(
        provider="anthropic",
        api_key="test-key",
        model="claude-sonnet-4-6",
        cache_enabled=False,
    )
