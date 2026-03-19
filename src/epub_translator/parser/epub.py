from typing import List

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from .base import AbstractParser
from ..models import Chapter, ContentBlock


class EPUBParser(AbstractParser):
    def __init__(self, filepath: str):
        self.book = epub.read_epub(filepath)

    def get_title(self) -> str:
        meta = self.book.get_metadata("DC", "title")
        return meta[0][0] if meta else "Untitled"

    def get_chapters(self) -> List[Chapter]:
        chapters = []
        for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            raw = item.get_content().decode("utf-8", errors="replace")
            soup = BeautifulSoup(raw, "html.parser")

            blocks: List[ContentBlock] = []
            chapter_title = ""

            for tag in soup.find_all(["h1", "h2", "h3", "p"]):
                text = tag.get_text(separator=" ", strip=True)
                if not text or len(text) < 3:
                    continue
                if not chapter_title and tag.name in ("h1", "h2"):
                    chapter_title = text
                blocks.append(ContentBlock(block_type=tag.name, text=text))

            # Skip completely empty documents (nav/toc stubs)
            if not blocks:
                continue

            chapters.append(Chapter(title=chapter_title, blocks=blocks))

        return chapters

    def list_chapters(self) -> None:
        """Print a numbered list of all chapters for preview."""
        chapters = self.get_chapters()
        title = self.get_title()
        print(f"书名：{title}")
        print(f"共 {len(chapters)} 章节：\n")
        for i, ch in enumerate(chapters, 1):
            label = (ch.title or "（无标题）")[:60]
            print(f"  {i:>3}. {label}  [{len(ch.blocks)} 段]")
        print("\n用法示例：--chapters 1-10  或  --chapters 1,3,5-8")
