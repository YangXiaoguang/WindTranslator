"""PDF renderer service — reads translated content from DB and generates PDF."""

from __future__ import annotations

import logging
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
)

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.project_repo import ProjectRepository
from ..repositories.chapter_repo import ChapterRepository
from .styles import register_fonts, build_styles

log = logging.getLogger(__name__)


class PDFRendererService:
    """Generate a Chinese PDF from translated content stored in the DB."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._project_repo = ProjectRepository(session)
        self._chapter_repo = ChapterRepository(session)

    async def render(
        self,
        project_id: str,
        output_path: str,
        chapter_indices: list[int] | None = None,
    ) -> str:
        """Render translated chapters to a PDF file.

        Args:
            project_id: The project whose chapters to render.
            output_path: Destination PDF file path.
            chapter_indices: 1-based indices to include. None = all.

        Returns:
            The absolute path of the generated PDF.
        """
        project = await self._project_repo.get_by_id(project_id)
        if project is None:
            raise ValueError(f"项目不存在: {project_id}")

        chapters = await self._chapter_repo.get_by_project(
            project_id, load_blocks=True,
        )
        if chapter_indices:
            idx_set = set(chapter_indices)
            chapters = [ch for ch in chapters if ch.index in idx_set]

        if not chapters:
            raise ValueError("没有可渲染的章节")

        # Validate output path is within the allowed output directory
        from ..storage import get_output_dir
        allowed_dir = get_output_dir(project_id).resolve()
        out = Path(output_path).resolve()
        if not str(out).startswith(str(allowed_dir)):
            raise ValueError(
                f"输出路径 {out} 不在允许目录 {allowed_dir} 内"
            )
        out.parent.mkdir(parents=True, exist_ok=True)

        self._build_pdf(project.title, chapters, str(out))

        # Persist output path
        project.output_path = str(out.resolve())
        await self.session.commit()

        log.info("PDF 已生成: %s", out)
        return str(out.resolve())

    @staticmethod
    def _build_pdf(
        book_title: str,
        chapters: list,
        output_path: str,
    ) -> None:
        """Synchronous PDF construction using ReportLab."""
        register_fonts()
        styles = build_styles()

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
        )

        def para(text: str, style_key: str) -> Paragraph | None:
            try:
                return Paragraph(xml_escape(text), styles[style_key])
            except Exception as exc:
                log.warning("段落渲染跳过: %s", exc)
                return None

        story: list = []

        # Title page
        story.append(Spacer(1, 5 * cm))
        title_p = para(book_title, "book_title")
        if title_p:
            story.append(title_p)
        story.append(PageBreak())

        for ch_idx, chapter in enumerate(chapters):
            if ch_idx > 0:
                story.append(PageBreak())

            heading_text = (
                (chapter.blocks[0].translated or chapter.title)
                if chapter.blocks
                else chapter.title
            ) or "（无标题）"

            heading_p = para(heading_text, "h1")
            body_items: list = []

            for block in chapter.blocks[1:]:
                text = block.translated or block.text
                if not text.strip():
                    continue
                style = block.block_type if block.block_type in styles else "p"
                p = para(text, style)
                if p:
                    body_items.append(p)

            if heading_p and body_items:
                story.append(KeepTogether([heading_p, body_items[0]]))
                story.extend(body_items[1:])
            elif heading_p:
                story.append(heading_p)

        doc.build(story)
