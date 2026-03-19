import logging
import re
import sys
import argparse
from pathlib import Path

from .config import load_config
from .parser.epub import EPUBParser
from .pipeline import TranslationPipeline

log = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )


def _list_chapters(epub_path: Path) -> None:
    EPUBParser(str(epub_path)).list_chapters()


def main() -> None:
    _setup_logging()

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
    parser.add_argument("--api-key", dest="api_key", help="覆盖配置：API Key")
    parser.add_argument("--base-url", dest="base_url", help="覆盖配置：自定义 API 地址（OpenAI 兼容）")
    parser.add_argument("--no-cache", action="store_true", help="禁用翻译缓存")
    parser.add_argument(
        "--chapters", metavar="RANGE",
        help="只处理指定章节，如 1-10、5、1,3,5-8（默认处理全部）",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="列出 EPUB 中所有章节编号和标题后退出（不翻译）",
    )
    args = parser.parse_args()

    epub_path = Path(args.input).expanduser().resolve()
    if not epub_path.exists():
        print(f"错误：文件不存在：{epub_path}", file=sys.stderr)
        sys.exit(1)

    if args.list:
        _list_chapters(epub_path)
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
    if args.no_cache:
        cfg.cache_enabled = False

    if not cfg.api_key or not cfg.api_key.strip():
        print(
            "错误：未提供 API Key。请在 translator.yaml、环境变量或 --api-key 中配置。",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.output:
        output_path = args.output
    elif args.chapters:
        # Whitelist: keep digits, hyphens, underscores — replace everything else
        safe_range = re.sub(r"[^\d\-]", "_", args.chapters)
        output_path = str(epub_path.parent / f"{epub_path.stem}_ch{safe_range}_zh.pdf")
    else:
        output_path = str(epub_path.parent / (epub_path.stem + "_zh.pdf"))

    TranslationPipeline().run(str(epub_path), output_path, cfg, chapter_range=args.chapters)
