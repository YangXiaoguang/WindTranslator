#!/usr/bin/env python3
"""End-to-end translation script using the server-side engine.

Usage:
    python scripts/translate_cli.py book.epub -o output.pdf
    python scripts/translate_cli.py book.pdf --chapters 1-3
    python scripts/translate_cli.py book.epub --provider anthropic --model claude-sonnet-4-6

This script demonstrates the full pipeline:
  1. Parse the input file and persist to SQLite
  2. Translate via LLM provider
  3. Render translated content to PDF

Environment variables:
    WT_DATABASE_URL   — SQLAlchemy URL (default: sqlite+aiosqlite:///./wind_translator.db)
    API_KEY           — LLM API key (or provider-specific: ANTHROPIC_API_KEY, etc.)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure src/ is on the path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "src"))

from server.database import async_session_factory, init_db
from server.parser.epub import EPUBParserService
from server.translator.engine import TranslationEngine
from server.translator.providers import get_provider
from server.renderer.pdf import PDFRendererService
from server.repositories.project_repo import ProjectRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

_SUPPORTED = {".epub", ".pdf"}


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    p = argparse.ArgumentParser(
        description="WindTranslator — 英文电子书翻译为中文 PDF（服务端引擎）",
    )
    p.add_argument("input", help="输入文件路径（.epub / .pdf）")
    p.add_argument("-o", "--output", help="输出 PDF 路径（默认：同名 _zh.pdf）")
    p.add_argument("--provider", default="anthropic", help="LLM provider")
    p.add_argument("--model", default="claude-sonnet-4-6", help="模型名称")
    p.add_argument("--api-key", dest="api_key", help="API Key")
    p.add_argument("--base-url", dest="base_url", help="自定义 API 端点")
    p.add_argument("--chapters", help="章节范围，如 1-3")
    return p


def _resolve_api_key(args: argparse.Namespace) -> str:
    """Resolve API key from args or environment."""
    if args.api_key:
        return args.api_key
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    env_var = env_map.get(args.provider, "API_KEY")
    key = os.environ.get(env_var) or os.environ.get("API_KEY")
    if not key:
        print(f"错误：未提供 API Key。设置 {env_var} 环境变量或使用 --api-key", file=sys.stderr)
        sys.exit(1)
    return key


def _parse_chapter_range(range_str: str) -> list[int]:
    """Parse '1-3' or '1,3,5' into a list of 1-based indices."""
    indices = []
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            indices.extend(range(int(start), int(end) + 1))
        else:
            indices.append(int(part))
    return sorted(set(indices))


async def _main(args: argparse.Namespace) -> None:
    """Async entry point."""
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"错误：文件不存在：{input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.suffix.lower() not in _SUPPORTED:
        print(f"错误：不支持的格式 {input_path.suffix}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or str(
        input_path.parent / f"{input_path.stem}_zh.pdf"
    )

    api_key = _resolve_api_key(args)
    chapter_indices = _parse_chapter_range(args.chapters) if args.chapters else None

    # Initialize DB tables
    await init_db()

    async with async_session_factory() as session:
        # 1. Parse
        log.info("[1/3] 解析文件：%s", input_path)
        parser_svc = EPUBParserService(session)
        project = await parser_svc.parse_and_persist(str(input_path))
        log.info("      书名：%s — %d 章, %d 块", project.title, project.total_chapters, project.total_blocks)

        # 2. Translate
        log.info("[2/3] 翻译（%s / %s）", args.provider, args.model)
        provider = get_provider(
            provider=args.provider,
            api_key=api_key,
            model=args.model,
            base_url=args.base_url,
        )

        def on_progress(done: int, total: int, title: str) -> None:
            pct = done / total * 100 if total else 0
            log.info("      进度：%d/%d (%.0f%%) — %s", done, total, pct, title)

        engine = TranslationEngine(
            session=session,
            provider=provider,
            on_progress=on_progress,
        )
        await engine.translate_project(project.id, chapter_indices)

        # 3. Render
        log.info("[3/3] 生成 PDF")
        renderer = PDFRendererService(session)
        final_path = await renderer.render(project.id, output_path, chapter_indices)
        log.info("完成！输出文件：%s", final_path)


def main() -> None:
    """Sync entry point."""
    args = _build_parser().parse_args()
    asyncio.run(_main(args))


if __name__ == "__main__":
    main()
