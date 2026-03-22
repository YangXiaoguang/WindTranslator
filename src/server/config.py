"""Application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Server-wide configuration.  All values can be overridden via env vars."""

    # ── Database ──
    database_url: str = "sqlite+aiosqlite:///./wind_translator.db"

    # ── Redis / Celery ──
    redis_url: str = "redis://localhost:6379/0"

    # ── File storage ──
    upload_dir: Path = Path("uploads")
    output_dir: Path = Path("outputs")

    # ── Encryption ──
    encryption_key: str = ""  # Fernet key; generate via Fernet.generate_key()

    # ── CORS ──
    allowed_origins: str = "http://localhost,http://localhost:5173,http://127.0.0.1:5173"

    # ── Translation defaults ──
    batch_char_limit: int = 2000
    max_retries: int = 3
    separator: str = "\n<<<SPLIT>>>\n"

    model_config = {"env_prefix": "WT_", "env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
