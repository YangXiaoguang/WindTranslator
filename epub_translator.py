#!/usr/bin/env python3
"""
EPUB to Chinese PDF Translator
Reads an English EPUB, translates it to professional Chinese via a configurable
LLM API (Anthropic Claude or any OpenAI-compatible service), and outputs a PDF.

Config file (translator.yaml) is searched in order:
  1. Path given via --config CLI flag
  2. ./translator.yaml  (current working directory)
  3. ~/.translator.yaml (home directory)
"""

import os
import sys
import time
import argparse
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from typing import List, Optional
from dataclasses import dataclass, field

import yaml
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


# ─── Configuration ──────────────────────────────────────────────────────────────

BATCH_CHAR_LIMIT = 2000   # soft cap for batching paragraphs
MAX_RETRIES = 3
SEPARATOR = "\n<<<SPLIT>>>\n"

# Default config — overridden by translator.yaml or CLI flags
DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-sonnet-4-6"

CONFIG_SEARCH_PATHS = [
    Path.cwd() / "translator.yaml",
    Path.home() / ".translator.yaml",
]


@dataclass
class TranslatorConfig:
    provider: str = DEFAULT_PROVIDER   # anthropic | openai | deepseek | custom
    api_key: Optional[str] = None
    model: str = DEFAULT_MODEL
    base_url: Optional[str] = None     # for openai-compatible endpoints


def load_config(config_path: Optional[str] = None) -> TranslatorConfig:
    """Load config from YAML file. Falls back to env vars when fields are absent."""
    paths = ([Path(config_path)] if config_path else []) + CONFIG_SEARCH_PATHS

    data: dict = {}
    for p in paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            print(f"[配置] 使用配置文件：{p}")
            break
    else:
        print("[配置] 未找到 translator.yaml，使用环境变量 / 命令行参数")

    cfg = TranslatorConfig(
        provider=data.get("provider", DEFAULT_PROVIDER),
        model=data.get("model", DEFAULT_MODEL),
        base_url=data.get("base_url"),
    )

    # api_key: config file > env var (provider-specific) > generic env var
    raw_key = data.get("api_key", "")
    if raw_key and raw_key != "YOUR_API_KEY_HERE":
        cfg.api_key = raw_key
    else:
        env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai":    "OPENAI_API_KEY",
            "deepseek":  "DEEPSEEK_API_KEY",
        }
        env_var = env_map.get(cfg.provider, "API_KEY")
        cfg.api_key = os.environ.get(env_var) or os.environ.get("API_KEY")

    return cfg


# ─── Data Models ────────────────────────────────────────────────────────────────

@dataclass
class ContentBlock:
    block_type: str   # h1, h2, h3, p
    text: str
    translated: str = ""


@dataclass
class Chapter:
    title: str
    blocks: List[ContentBlock] = field(default_factory=list)


# ─── Chapter Range Parser ────────────────────────────────────────────────────────

def parse_chapter_range(spec: str, total: int) -> List[int]:
    """
    Parse a chapter range spec into a sorted list of 0-based indices.

    Accepted formats (1-based, inclusive):
      "1-10"     → chapters 1 to 10
      "5"        → chapter 5 only
      "1,3,5-8"  → chapters 1, 3, 5, 6, 7, 8
    """
    def _to_int(s: str, context: str) -> int:
        try:
            return int(s)
        except ValueError:
            raise ValueError(f"章节范围格式错误：'{context}' 不是有效数字")

    indices = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            raw_lo, raw_hi = part.split("-", 1)
            lo = _to_int(raw_lo.strip(), raw_lo.strip())
            hi = _to_int(raw_hi.strip(), raw_hi.strip())
            if lo < 1 or hi > total or lo > hi:
                raise ValueError(
                    f"范围 {lo}-{hi} 超出有效章节数（1-{total}），"
                    f"请先用 --list 查看章节列表"
                )
            indices.update(range(lo - 1, hi))
        else:
            n = _to_int(part, part)
            if n < 1 or n > total:
                raise ValueError(
                    f"章节 {n} 超出有效范围（1-{total}），"
                    f"请先用 --list 查看章节列表"
                )
            indices.add(n - 1)
    if not indices:
        raise ValueError(f"章节范围 '{spec}' 未匹配任何章节")
    return sorted(indices)


# ─── EPUB Parser ────────────────────────────────────────────────────────────────

class EPUBParser:
    def __init__(self, filepath: str):
        self.book = epub.read_epub(filepath)

    def get_title(self) -> str:
        meta = self.book.get_metadata("DC", "title")
        return meta[0][0] if meta else "Untitled"

    def get_chapters(self) -> List[Chapter]:
        chapters = []
        for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            raw = item.get_content().decode("utf-8", errors="ignore")
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

            # Skip nav/toc pages with almost no content
            if len(blocks) < 2:
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
        print(f"\n用法示例：--chapters 1-10  或  --chapters 1,3,5-8")


# ─── Translator ─────────────────────────────────────────────────────────────────

def _build_client(cfg: TranslatorConfig):
    """Return an API client based on provider."""
    provider = cfg.provider.lower()
    if provider == "anthropic":
        import anthropic as _anthropic
        return _anthropic.Anthropic(api_key=cfg.api_key), "anthropic"
    else:
        # openai / deepseek / custom — all use the OpenAI-compatible SDK
        try:
            import openai as _openai
        except ImportError:
            print("错误：使用 openai/deepseek/custom provider 需安装 openai 包：pip install openai",
                  file=sys.stderr)
            sys.exit(1)
        kwargs = {"api_key": cfg.api_key}
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        elif provider == "deepseek":
            kwargs["base_url"] = "https://api.deepseek.com/v1"
        return _openai.OpenAI(**kwargs), "openai"


_SYSTEM_PROMPT_FILE = Path(__file__).parent / "system_prompt.md"


class Translator:
    def __init__(self, cfg: TranslatorConfig):
        self.cfg = cfg
        self.client, self.client_type = _build_client(cfg)
        self.SYSTEM_PROMPT = _SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()

    def _call_api(self, text: str) -> str:
        """Single API call with exponential backoff retry."""
        for attempt in range(MAX_RETRIES):
            try:
                if self.client_type == "anthropic":
                    resp = self.client.messages.create(
                        model=self.cfg.model,
                        max_tokens=4096,
                        system=self.SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": text}],
                    )
                    return resp.content[0].text.strip()
                else:
                    resp = self.client.chat.completions.create(
                        model=self.cfg.model,
                        max_tokens=4096,
                        messages=[
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": text},
                        ],
                    )
                    content = resp.choices[0].message.content
                    return (content or "").strip()
            except Exception as e:
                wait = 2 ** attempt
                print(f"    API错误，{wait}秒后重试 ({attempt+1}/{MAX_RETRIES}): {e}")
                time.sleep(wait)
        print("    翻译失败，保留原文")
        return text

    def _translate_batch(self, texts: List[str]) -> List[str]:
        """Translate a batch of texts, validate count, fall back to one-by-one."""
        if not texts:
            return []
        joined = SEPARATOR.join(texts)
        result = self._call_api(joined)
        parts = [p.strip() for p in result.split("<<<SPLIT>>>")]
        if len(parts) == len(texts):
            return parts
        # Fallback: translate individually
        print(f"    批量分割数量不符 (期望{len(texts)}，得到{len(parts)})，逐条翻译")
        return [self._call_api(t) for t in texts]

    def translate_chapter(self, chapter: Chapter) -> Chapter:
        """Translate all blocks in a chapter in place."""
        heading_types = {"h1", "h2", "h3"}

        # Collect pending paragraph batch
        pending_texts: List[str] = []
        pending_indices: List[int] = []

        def flush_pending():
            if not pending_texts:
                return
            translated = self._translate_batch(list(pending_texts))
            for idx, t in zip(pending_indices, translated):
                chapter.blocks[idx].translated = t
            pending_texts.clear()
            pending_indices.clear()

        for i, block in enumerate(chapter.blocks):
            if block.block_type in heading_types:
                flush_pending()
                result = self._translate_batch([block.text])
                block.translated = result[0]
            else:
                pending_texts.append(block.text)
                pending_indices.append(i)
                if sum(len(t) for t in pending_texts) >= BATCH_CHAR_LIMIT:
                    flush_pending()

        flush_pending()
        return chapter


# ─── PDF Generator ──────────────────────────────────────────────────────────────

def _register_fonts():
    if "STSong-Light" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def _build_styles() -> dict:
    base = dict(fontName="STSong-Light")
    return {
        "book_title": ParagraphStyle(
            "BookTitle", **base, fontSize=22, leading=30,
            spaceAfter=16, alignment=1,
        ),
        "h1": ParagraphStyle(
            "H1", **base, fontSize=17, leading=26,
            spaceBefore=20, spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2", **base, fontSize=14, leading=22,
            spaceBefore=16, spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "H3", **base, fontSize=12, leading=20,
            spaceBefore=12, spaceAfter=6,
        ),
        "p": ParagraphStyle(
            "Body", **base, fontSize=11, leading=19,
            spaceAfter=7, firstLineIndent=22,
        ),
    }


class PDFGenerator:
    def __init__(self, output_path: str, book_title: str):
        self.output_path = output_path
        self.book_title = book_title
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            topMargin=2.5 * cm, bottomMargin=2.5 * cm,
        )
        self.styles = _build_styles()

    def _para(self, text: str, style_key: str) -> Optional[Paragraph]:
        safe = xml_escape(text)
        try:
            return Paragraph(safe, self.styles[style_key])
        except Exception as e:
            print(f"  警告：段落渲染跳过: {e}")
            return None

    def build(self, chapters: List[Chapter]):
        story = []

        # Title page
        story.append(Spacer(1, 5 * cm))
        title_para = self._para(self.book_title, "book_title")
        if title_para:
            story.append(title_para)
        story.append(PageBreak())

        for ch_idx, chapter in enumerate(chapters):
            if ch_idx > 0:
                story.append(PageBreak())

            heading_text = chapter.blocks[0].translated or chapter.title if chapter.blocks else chapter.title
            heading_para = self._para(heading_text, "h1")
            body_start = []

            for block in chapter.blocks[1:]:
                text = block.translated or block.text
                if not text.strip():
                    continue
                style = block.block_type if block.block_type in self.styles else "p"
                p = self._para(text, style)
                if p:
                    body_start.append(p)

            # Keep heading with first paragraph to avoid orphans
            if heading_para and body_start:
                story.append(KeepTogether([heading_para, body_start[0]]))
                story.extend(body_start[1:])
            elif heading_para:
                story.append(heading_para)

        self.doc.build(story)
        print(f"\nPDF 已生成：{self.output_path}")


# ─── Main Pipeline ───────────────────────────────────────────────────────────────

def translate_epub(epub_path: str, output_path: str, cfg: TranslatorConfig,
                   chapter_range: Optional[str] = None):
    _register_fonts()

    print(f"[1/3] 解析 EPUB：{epub_path}")
    parser = EPUBParser(epub_path)
    book_title = parser.get_title()
    all_chapters = parser.get_chapters()
    print(f"      书名：{book_title}")
    print(f"      全书章节数：{len(all_chapters)}")

    # Apply chapter range filter
    if chapter_range:
        try:
            indices = parse_chapter_range(chapter_range, len(all_chapters))
        except ValueError as e:
            print(f"错误：{e}", file=sys.stderr)
            sys.exit(1)
        chapters = [all_chapters[i] for i in indices]
        first, last = indices[0] + 1, indices[-1] + 1
        print(f"      处理章节：{chapter_range}（共 {len(chapters)} 章，第 {first}-{last} 章）")
    else:
        chapters = all_chapters
        print(f"      处理章节：全部（{len(chapters)} 章）")

    print(f"\n[2/3] 翻译内容（{cfg.provider} / {cfg.model}）")
    translator = Translator(cfg)
    for i, chapter in enumerate(chapters):
        title_preview = (chapter.title or f"章节{i+1}")[:50]
        print(f"  [{i+1}/{len(chapters)}] {title_preview}... ({len(chapter.blocks)} 段)")
        translator.translate_chapter(chapter)

    print(f"\n[3/3] 生成 PDF")
    pdf = PDFGenerator(output_path, book_title)
    pdf.build(chapters)
    print(f"\n完成！输出文件：{output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="将英文 EPUB 翻译为中文 PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "章节范围示例：\n"
            "  --chapters 1-10       处理第 1 到第 10 章\n"
            "  --chapters 5          只处理第 5 章\n"
            "  --chapters 1,3,5-8   处理第 1、3、5、6、7、8 章\n\n"
            "预览章节列表：\n"
            "  --list                列出所有章节编号和标题后退出"
        ),
    )
    parser.add_argument("input", help="输入的 EPUB 文件路径")
    parser.add_argument("-o", "--output", help="输出 PDF 路径（默认：同名 _zh.pdf）")
    parser.add_argument("--config", help="配置文件路径（默认自动搜索 translator.yaml）")
    parser.add_argument("--provider", help="覆盖配置：模型服务商（anthropic/openai/deepseek/custom）")
    parser.add_argument("--model", help="覆盖配置：模型名称")
    parser.add_argument("--api-key", help="覆盖配置：API Key")
    parser.add_argument("--base-url", help="覆盖配置：自定义 API 地址（OpenAI 兼容）")
    parser.add_argument(
        "--chapters",
        metavar="RANGE",
        help="只处理指定章节，如 1-10、5、1,3,5-8（默认处理全部）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出 EPUB 中所有章节编号和标题后退出（不翻译）",
    )
    args = parser.parse_args()

    epub_path = Path(args.input).expanduser().resolve()
    if not epub_path.exists():
        print(f"错误：文件不存在：{epub_path}", file=sys.stderr)
        sys.exit(1)

    # --list: preview chapters and exit, no API key needed
    if args.list:
        EPUBParser(str(epub_path)).list_chapters()
        return

    cfg = load_config(args.config)
    # CLI flags override config file
    if args.provider:
        cfg.provider = args.provider
    if args.model:
        cfg.model = args.model
    if args.api_key:
        cfg.api_key = args.api_key
    if args.base_url:
        cfg.base_url = args.base_url

    if not cfg.api_key:
        print("错误：未提供 API Key。请在 translator.yaml、环境变量或 --api-key 中配置。",
              file=sys.stderr)
        sys.exit(1)

    # Auto-suffix output filename when processing a subset of chapters
    if args.output:
        output_path = args.output
    elif args.chapters:
        safe_range = args.chapters.replace(",", "_").replace("-", "-")
        output_path = str(epub_path.parent / f"{epub_path.stem}_ch{safe_range}_zh.pdf")
    else:
        output_path = str(epub_path.parent / (epub_path.stem + "_zh.pdf"))

    translate_epub(str(epub_path), output_path, cfg, chapter_range=args.chapters)


if __name__ == "__main__":
    main()
