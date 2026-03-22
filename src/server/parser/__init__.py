"""Parsers that extract chapters from ebooks and persist to the database."""

from .epub import EPUBParserService

__all__ = ["EPUBParserService"]
