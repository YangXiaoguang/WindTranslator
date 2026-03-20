import logging
from typing import Optional

from .config import TranslatorConfig
from .parser import get_parser
from .translator.llm import LLMTranslator
from .renderer.pdf import PDFRenderer
from .utils.chapter_range import parse_chapter_range

log = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    """Raised for expected pipeline failures (bad input, bad range, etc.)."""


class TranslationPipeline:
    """Orchestrates parse → translate → render."""

    def run(
        self,
        input_path: str,
        output_path: str,
        cfg: TranslatorConfig,
        chapter_range: Optional[str] = None,
    ) -> None:
        # ── 1. Parse ──────────────────────────────────────────────────────────
        log.info("[1/3] 解析文件：%s", input_path)
        parser = get_parser(input_path)
        book_title = parser.get_title()
        all_chapters = parser.get_chapters()
        log.info("      书名：%s", book_title)
        log.info("      全书章节数：%d", len(all_chapters))

        if not all_chapters:
            raise PipelineError("未提取到任何章节，请检查文件内容")

        if chapter_range:
            try:
                indices = parse_chapter_range(chapter_range, len(all_chapters))
            except ValueError as e:
                raise PipelineError(str(e)) from e
            chapters = [all_chapters[i] for i in indices]
            first, last = indices[0] + 1, indices[-1] + 1
            log.info(
                "      处理章节：%s（共 %d 章，第 %d-%d 章）",
                chapter_range, len(chapters), first, last,
            )
        else:
            chapters = all_chapters
            log.info("      处理章节：全部（%d 章）", len(chapters))

        # ── 2. Translate ──────────────────────────────────────────────────────
        log.info("[2/3] 翻译内容（%s / %s）", cfg.provider, cfg.model)
        translator: Optional[LLMTranslator] = None
        try:
            translator = LLMTranslator(cfg)
            for i, chapter in enumerate(chapters):
                title_preview = (chapter.title or f"章节{i + 1}")[:50]
                log.info(
                    "  [%d/%d] %s... (%d 段)",
                    i + 1, len(chapters), title_preview, len(chapter.blocks),
                )
                translator.translate_chapter(chapter)
        finally:
            if translator is not None:
                translator.close()

        # ── 3. Render ─────────────────────────────────────────────────────────
        log.info("[3/3] 生成 PDF")
        PDFRenderer(book_title).render(chapters, output_path)
        log.info("完成！输出文件：%s", output_path)
