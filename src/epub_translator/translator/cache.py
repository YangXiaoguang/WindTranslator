import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


class TranslationCache:
    """
    SQLite-backed content-hash → translation cache.

    Cache key includes model + provider so switching either one
    automatically invalidates stale entries.
    """

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                source_hash TEXT PRIMARY KEY,
                translation TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        log.debug("翻译缓存：%s", db_path)

    @staticmethod
    def _hash(text: str, model: str, provider: str) -> str:
        key = f"{provider}:{model}:{text}"
        return hashlib.sha256(key.encode()).hexdigest()

    def get(self, text: str, model: str, provider: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT translation FROM translations WHERE source_hash = ?",
            (self._hash(text, model, provider),),
        ).fetchone()
        return row[0] if row else None

    def put(self, text: str, model: str, provider: str, translation: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO translations (source_hash, translation) VALUES (?, ?)",
            (self._hash(text, model, provider), translation),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
