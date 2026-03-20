import logging
import re
import sys
import argparse
from pathlib import Path

from .config import load_config
from .parser import get_parser, _SUPPORTED_FORMATS
from .pipeline import TranslationPipeline, PipelineError

# Valid provider names — kept in sync with providers/__init__.py
_VALID_PROVIDERS = {"anthropic", "openai", "deepseek", "custom"}


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(levelname)s %(name)s: %(message)s" if verbose else "%(message)s"
    logging.basicConfig(level=level, format=fmt, stream=sys.stdout)


def _version() -> str:
    try:
        from importlib.metadata import version
        return version("epub-translator")
    except Exception:
        return "unknown"


def _build_arg_parser() -> argparse.ArgumentParser:
    supported_exts = " / ".join(_SUPPORTED_FORMATS)
    arg_parser = argparse.ArgumentParser(
        prog="epub-translator",
        description=f"将英文 {supported_exts} 电子书翻译为中文 PDF",
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
    arg_parser.add_argument("input", help=f"输入文件路径（{supported_exts}）")
    arg_parser.add_argument("-o", "--output", help="输出 PDF 路径（默认：同名 _zh.pdf）")
    arg_parser.add_argument(
        "--config", help="配置文件路径（默认自动搜索 translator.yaml）"
    )
    arg_parser.add_argument(
        "--provider",
        choices=sorted(_VALID_PROVIDERS),
        metavar="NAME",
        help=f"覆盖配置：模型服务商（{' | '.join(sorted(_VALID_PROVIDERS))}）",
    )
    arg_parser.add_argument("--model", help="覆盖配置：模型名称")
    arg_parser.add_argument("--api-key", dest="api_key", help="覆盖配置：API Key")
    arg_parser.add_argument(
        "--base-url", dest="base_url",
        help="覆盖配置：自定义 API 地址（OpenAI 兼容端点）",
    )
    arg_parser.add_argument("--no-cache", action="store_true", help="禁用翻译缓存")
    arg_parser.add_argument(
        "--chapters", metavar="RANGE",
        help="只处理指定章节，如 1-10、5、1,3,5-8（默认处理全部）",
    )
    arg_parser.add_argument(
        "--list", action="store_true",
        help="列出文件中所有章节编号和标题后退出（不翻译）",
    )
    arg_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="输出 DEBUG 级别日志（含模块名、日志级别）",
    )
    arg_parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_version()}"
    )
    return arg_parser


def _resolve_output_path(input_path: Path, args: argparse.Namespace) -> str:
    if args.output:
        output_path = Path(args.output)
    elif args.chapters:
        safe_range = re.sub(r"[^\d\-]", "_", args.chapters)
        output_path = input_path.parent / f"{input_path.stem}_ch{safe_range}_zh.pdf"
    else:
        output_path = input_path.parent / (input_path.stem + "_zh.pdf")

    # Validate output directory exists before starting (potentially long) translation
    if not output_path.parent.exists():
        print(
            f"错误：输出目录不存在：{output_path.parent}",
            file=sys.stderr,
        )
        sys.exit(1)

    return str(output_path)


def main() -> None:
    arg_parser = _build_arg_parser()
    args = arg_parser.parse_args()

    _setup_logging(verbose=args.verbose)

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"错误：文件不存在：{input_path}", file=sys.stderr)
        sys.exit(1)

    # Validate format by extension — cheap, no file I/O
    if input_path.suffix.lower() not in _SUPPORTED_FORMATS:
        supported = ", ".join(_SUPPORTED_FORMATS)
        print(
            f"错误：不支持的文件格式 {input_path.suffix!r}，目前支持：{supported}",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.list:
        # Only build the parser when --list actually needs it
        doc_parser = get_parser(str(input_path))
        doc_parser.list_chapters()
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

    output_path = _resolve_output_path(input_path, args)

    try:
        TranslationPipeline().run(
            str(input_path), output_path, cfg, chapter_range=args.chapters
        )
    except PipelineError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
