import logging
from typing import List, Optional
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether,
)

from .base import AbstractRenderer
from .styles import register_fonts, build_styles
from ..models import Chapter

log = logging.getLogger(__name__)


class PDFRenderer(AbstractRenderer):
    def __init__(self, book_title: str):
        self.book_title = book_title

    def render(self, chapters: List[Chapter], output_path: str) -> None:
        register_fonts()
        styles = build_styles()

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            topMargin=2.5 * cm, bottomMargin=2.5 * cm,
        )

        def para(text: str, style_key: str) -> Optional[Paragraph]:
            try:
                return Paragraph(xml_escape(text), styles[style_key])
            except Exception as e:
                log.warning("段落渲染跳过: %s", e)
                return None

        story = []

        # Title page
        story.append(Spacer(1, 5 * cm))
        title_para = para(self.book_title, "book_title")
        if title_para:
            story.append(title_para)
        story.append(PageBreak())

        for ch_idx, chapter in enumerate(chapters):
            if ch_idx > 0:
                story.append(PageBreak())

            heading_text = (
                (chapter.blocks[0].translated or chapter.title)
                if chapter.blocks
                else chapter.title
            ) or "（无标题）"
            heading_para = para(heading_text, "h1")
            body_items = []

            for block in chapter.blocks[1:]:
                text = block.translated or block.text
                if not text.strip():
                    continue
                style = block.block_type if block.block_type in styles else "p"
                p = para(text, style)
                if p:
                    body_items.append(p)

            # Keep heading with its first paragraph to avoid orphaned headings
            if heading_para and body_items:
                story.append(KeepTogether([heading_para, body_items[0]]))
                story.extend(body_items[1:])
            elif heading_para:
                story.append(heading_para)

        doc.build(story)
        log.info("PDF 已生成：%s", output_path)
