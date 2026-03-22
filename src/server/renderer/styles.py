"""Font registration and paragraph styles for PDF output."""

from __future__ import annotations

from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

_FONT = "STSong-Light"


def register_fonts() -> None:
    """Register the Chinese CID font if not already registered."""
    if _FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(_FONT))


def build_styles() -> dict[str, ParagraphStyle]:
    """Return a dict of named ReportLab ParagraphStyles."""
    base = dict(fontName=_FONT)
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
