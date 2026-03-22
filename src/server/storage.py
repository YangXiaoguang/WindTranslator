"""File storage utilities for uploads and outputs."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .config import get_settings

log = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def _ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_upload_dir(project_id: str) -> Path:
    """Return the upload directory for a given project."""
    settings = get_settings()
    return _ensure_dir(settings.upload_dir / project_id)


def get_output_dir(project_id: str) -> Path:
    """Return the output directory for a given project."""
    settings = get_settings()
    return _ensure_dir(settings.output_dir / project_id)


def save_upload(project_id: str, filename: str, content: bytes) -> Path:
    """Persist uploaded file bytes to disk and return the full path."""
    if len(content) > MAX_UPLOAD_SIZE:
        raise ValueError(
            f"文件大小 ({len(content) / 1024 / 1024:.1f}MB) "
            f"超过限制 ({MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB)"
        )
    upload_dir = get_upload_dir(project_id)
    dest = upload_dir / filename
    dest.write_bytes(content)
    log.info("文件已保存: %s (%d bytes)", dest, len(content))
    return dest


def cleanup_project(project_id: str) -> None:
    """Remove all files (upload + output) for a project."""
    settings = get_settings()
    for base in (settings.upload_dir, settings.output_dir):
        target = base / project_id
        if target.exists():
            shutil.rmtree(target)
            log.info("已删除: %s", target)
