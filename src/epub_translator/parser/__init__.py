from pathlib import Path

from .base import AbstractParser
from .epub import EPUBParser
from .pdf import PDFParser

__all__ = ["AbstractParser", "EPUBParser", "PDFParser", "get_parser", "_SUPPORTED_FORMATS"]

_SUPPORTED_FORMATS = {
    ".epub": EPUBParser,
    ".pdf": PDFParser,
}


def get_parser(filepath: str) -> AbstractParser:
    """Return the correct parser for *filepath* based on its file extension."""
    ext = Path(filepath).suffix.lower()
    parser_cls = _SUPPORTED_FORMATS.get(ext)
    if parser_cls is None:
        supported = ", ".join(_SUPPORTED_FORMATS)
        raise ValueError(
            f"不支持的文件格式 {ext!r}，目前支持：{supported}"
        )
    return parser_cls(filepath)
