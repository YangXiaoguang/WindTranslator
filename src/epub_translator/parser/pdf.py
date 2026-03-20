"""
PDF parser: extracts chapters from a PDF file using font-size heuristics.

Algorithm
---------
1. Extract all words from every page via pdfplumber, preserving font-size metadata.
2. Group words into visual lines by vertical proximity.
3. Compute the median font size across the entire document as the body baseline.
4. Lines whose average font size >= baseline * HEADING_RATIO are headings.
   The two largest distinct heading sizes map to h1 / h2 (chapter splits);
   the next maps to h3.
5. Consecutive body lines are merged into a single ContentBlock paragraph and
   flushed when a heading is hit or the accumulated text exceeds PARA_CHAR_LIMIT.
6. PDFs with no detectable headings are returned as a single chapter.
"""

import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .base import AbstractParser
from ..models import Chapter, ContentBlock

# ── Tuning constants ───────────────────────────────────────────────────────────
_MIN_FONT_PT = 4.0       # ignore sub-4pt glyphs (watermarks, hidden text)
_MIN_TEXT_LEN = 3        # skip very short text fragments
_HEADING_RATIO = 1.25    # font size >= median * ratio → heading
_BOLD_RATIO = 1.10       # bold text >= median * ratio → at least h3
_LINE_GAP_FACTOR = 0.5   # words within font_size * factor of same top → same line
_PARA_CHAR_LIMIT = 800   # flush accumulated paragraph at this character count


@dataclass
class _Line:
    text: str
    size: float   # average font size of all words on the line
    bold: bool    # True if any word uses a Bold font variant
    page: int


def _open_pdfplumber():
    """Lazy import so pdfplumber is optional until a PDF is actually opened."""
    try:
        import pdfplumber
        return pdfplumber
    except ImportError:
        raise ImportError(
            "需安装 pdfplumber 以支持 PDF 输入：pip install pdfplumber"
        )


class PDFParser(AbstractParser):
    """Reads a PDF file and presents it as a list of :class:`Chapter` objects."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    # ── Public interface ───────────────────────────────────────────────────────

    def get_title(self) -> str:
        pdfplumber = _open_pdfplumber()
        with pdfplumber.open(self.filepath) as pdf:
            meta = pdf.metadata or {}
            title = meta.get("Title") or meta.get("title", "")
            return title.strip() if title and title.strip() else Path(self.filepath).stem

    def get_chapters(self) -> List[Chapter]:
        lines = self._extract_lines()
        classified = self._classify(lines)
        return self._build_chapters(classified)

    def list_chapters(self) -> None:
        """Print a numbered list of all detected chapters for preview."""
        chapters = self.get_chapters()
        title = self.get_title()
        print(f"书名：{title}")
        print(f"共 {len(chapters)} 章节：\n")
        for i, ch in enumerate(chapters, 1):
            label = (ch.title or "（无标题）")[:60]
            print(f"  {i:>3}. {label}  [{len(ch.blocks)} 段]")
        print("\n用法示例：--chapters 1-10  或  --chapters 1,3,5-8")

    # ── Private helpers ────────────────────────────────────────────────────────

    def _extract_lines(self) -> List[_Line]:
        """Extract visual lines from all pages with font-size metadata."""
        pdfplumber = _open_pdfplumber()
        lines: List[_Line] = []

        with pdfplumber.open(self.filepath) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                words = page.extract_words(
                    extra_attrs=["fontname", "size"],
                    use_text_flow=True,
                )
                if not words:
                    continue

                # Group words into lines by vertical proximity.
                # Words whose `top` differs by at most (font_size * factor) are
                # considered to be on the same line.
                line_groups: List[List[dict]] = []
                for word in words:
                    if not word.get("text", "").strip():
                        continue
                    font_size = word.get("size") or 12.0
                    tolerance = font_size * _LINE_GAP_FACTOR
                    placed = False
                    for group in reversed(line_groups):
                        if abs(word["top"] - group[0]["top"]) <= tolerance:
                            group.append(word)
                            placed = True
                            break
                    if not placed:
                        line_groups.append([word])

                for group in line_groups:
                    text = " ".join(w["text"] for w in group).strip()
                    if not text:
                        continue
                    sizes = [
                        w["size"] for w in group
                        if w.get("size") and w["size"] > _MIN_FONT_PT
                    ]
                    if not sizes:
                        continue
                    avg_size = statistics.mean(sizes)
                    is_bold = any(
                        "bold" in (w.get("fontname") or "").lower() for w in group
                    )
                    lines.append(_Line(
                        text=text,
                        size=avg_size,
                        bold=is_bold,
                        page=page_num,
                    ))

        return lines

    @staticmethod
    def _classify(lines: List[_Line]) -> List[Tuple[str, str]]:
        """
        Assign a block_type (h1/h2/h3/p) to each line.

        Returns a list of (block_type, text) tuples in document order.
        """
        if not lines:
            return []

        body_size = statistics.median(l.size for l in lines)
        heading_threshold = body_size * _HEADING_RATIO
        bold_threshold = body_size * _BOLD_RATIO

        # Collect distinct heading sizes and map to levels h1, h2, h3
        heading_sizes = sorted(
            {round(l.size, 1) for l in lines if l.size >= heading_threshold},
            reverse=True,
        )
        level_map = {s: f"h{i + 1}" for i, s in enumerate(heading_sizes[:3])}

        result: List[Tuple[str, str]] = []
        for line in lines:
            rounded = round(line.size, 1)
            if rounded in level_map:
                block_type = level_map[rounded]
            elif line.bold and line.size >= bold_threshold:
                block_type = "h3"
            else:
                block_type = "p"
            result.append((block_type, line.text))

        return result

    def _build_chapters(
        self, classified: List[Tuple[str, str]]
    ) -> List[Chapter]:
        """Convert (block_type, text) pairs into Chapter objects."""
        chapters: List[Chapter] = []
        current: Optional[Chapter] = None
        pending: List[str] = []   # body lines accumulating into one paragraph

        def flush_para() -> None:
            if not pending or current is None:
                pending.clear()
                return
            text = " ".join(pending).strip()
            if len(text) >= _MIN_TEXT_LEN:
                current.blocks.append(ContentBlock(block_type="p", text=text))
            pending.clear()

        def commit_chapter() -> None:
            nonlocal current
            if current is not None and current.blocks:
                chapters.append(current)
            current = None

        for block_type, text in classified:
            text = text.strip()
            if len(text) < _MIN_TEXT_LEN:
                continue

            if block_type in ("h1", "h2"):
                # Start a new chapter
                flush_para()
                commit_chapter()
                current = Chapter(title=text, blocks=[])
                current.blocks.append(ContentBlock(block_type=block_type, text=text))

            elif block_type == "h3":
                flush_para()
                if current is None:
                    current = Chapter(title="", blocks=[])
                current.blocks.append(ContentBlock(block_type="h3", text=text))

            else:  # body paragraph
                if current is None:
                    current = Chapter(title="", blocks=[])
                pending.append(text)
                # Flush when accumulated text is long enough to be a paragraph
                if sum(len(s) for s in pending) >= _PARA_CHAR_LIMIT:
                    flush_para()

        flush_para()
        commit_chapter()

        # Fallback: no headings detected → treat entire document as one chapter
        if not chapters:
            all_blocks = [
                ContentBlock(block_type="p", text=t)
                for _, t in classified
                if len(t) >= _MIN_TEXT_LEN
            ]
            if all_blocks:
                chapters.append(Chapter(
                    title=Path(self.filepath).stem,
                    blocks=all_blocks,
                ))

        return chapters
