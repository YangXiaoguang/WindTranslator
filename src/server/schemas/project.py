"""Pydantic schemas for TranslationProject API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    """Summary of a project (used in list views)."""

    id: str
    filename: str
    format: str
    title: str
    total_chapters: int
    total_blocks: int
    file_size: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChapterPreview(BaseModel):
    """Lightweight chapter info for project detail view."""

    id: str
    index: int
    title: str
    block_count: int
    preview_text: str
    status: str

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectResponse):
    """Full project with chapters (used in detail view)."""

    chapters: list[ChapterPreview] = []
