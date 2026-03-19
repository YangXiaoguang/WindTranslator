import logging
import re
from pathlib import Path
from typing import List, Optional

from ..models import Chapter
from ..config import TranslatorConfig, BATCH_CHAR_LIMIT, SEPARATOR
from .providers import get_provider, LLMProvider
from .cache import TranslationCache

log = logging.getLogger(__name__)

# Fallback used only when system_prompt.md is not found
_FALLBACK_SYSTEM_PROMPT = (
    "你是一位专业翻译专家，将英文书籍原文译为简体中文。要求：\n"
    "1. 译文专业、流畅，符合中文表达习惯\n"
    "2. 保持原文语气与段落结构\n"
    "3. 输入段落之间用 <<<SPLIT>>> 分隔，输出必须保持相同数量的段落，"
    "   仍用 <<<SPLIT>>> 分隔，不得增删段落或添加任何说明文字"
)


class LLMTranslator:
    def __init__(self, cfg: TranslatorConfig):
        self.cfg = cfg
        self.provider: LLMProvider = get_provider(cfg)
        self.system_prompt: str = self._load_system_prompt(cfg.system_prompt_path)
        self.cache: Optional[TranslationCache] = (
            TranslationCache(cfg.cache_db) if cfg.cache_enabled else None
        )

    @staticmethod
    def _load_system_prompt(path: Optional[Path]) -> str:
        if path and Path(path).exists():
            return Path(path).read_text(encoding="utf-8").strip()
        log.warning("未找到 system_prompt.md，使用内置提示词")
        return _FALLBACK_SYSTEM_PROMPT

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _call(self, text: str) -> str:
        """API call with transparent cache read/write."""
        if self.cache:
            cached = self.cache.get(text, self.cfg.model, self.cfg.provider)
            if cached is not None:
                log.debug("缓存命中（%d 字符）", len(text))
                return cached

        result = self.provider.complete(self.system_prompt, text)

        if self.cache:
            self.cache.put(text, self.cfg.model, self.cfg.provider, result)
        return result

    def _translate_batch(self, texts: List[str]) -> List[str]:
        """Translate texts as a single batched request; fall back to one-by-one."""
        if not texts:
            return []
        joined = SEPARATOR.join(texts)
        result = self._call(joined)
        # Use regex split so extra whitespace / newlines around the marker are handled
        raw_parts = re.split(r"\s*<<<SPLIT>>>\s*", result.strip())
        parts = [p.strip() for p in raw_parts if p.strip()]
        if len(parts) == len(texts):
            return parts
        log.warning(
            "批量分割数量不符（期望 %d，得到 %d），逐条翻译", len(texts), len(parts)
        )
        return [self._call(t) for t in texts]

    # ── Public API ─────────────────────────────────────────────────────────────

    def translate_chapter(self, chapter: Chapter) -> Chapter:
        """Translate all blocks in a chapter in-place and return it."""
        heading_types = {"h1", "h2", "h3"}
        pending_texts: List[str] = []
        pending_indices: List[int] = []

        def flush() -> None:
            if not pending_texts:
                return
            translated = self._translate_batch(list(pending_texts))
            for idx, t in zip(pending_indices, translated):
                chapter.blocks[idx].translated = t
            pending_texts.clear()
            pending_indices.clear()

        for i, block in enumerate(chapter.blocks):
            if block.block_type in heading_types:
                flush()
                block.translated = self._translate_batch([block.text])[0]
            else:
                pending_texts.append(block.text)
                pending_indices.append(i)
                if sum(len(t) for t in pending_texts) >= BATCH_CHAR_LIMIT:
                    flush()

        flush()
        return chapter

    def close(self) -> None:
        if self.cache:
            self.cache.close()
