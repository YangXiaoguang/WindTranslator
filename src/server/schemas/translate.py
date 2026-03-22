"""Pydantic schemas for translation-related endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    """Body for POST /api/projects/{id}/translate."""

    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model identifier")
    api_key: str = Field(..., description="Plain-text API key")
    base_url: Optional[str] = Field(None, description="Custom API endpoint")
    chapter_range: Optional[str] = Field(
        None,
        description="Chapter range, e.g. '1-5' or '1,3,7-10'. None = all.",
    )


class ProgressResponse(BaseModel):
    """Response for GET /api/projects/{id}/progress."""

    project_id: str
    status: str
    total_blocks: int = 0
    completed_blocks: int = 0
    percent: float = 0.0
    current_chapter: Optional[str] = None
    error_message: Optional[str] = None


class TestKeyRequest(BaseModel):
    """Body for POST /api/config/test-key."""

    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None


class TestKeyResponse(BaseModel):
    """Response for POST /api/config/test-key."""

    success: bool
    message: str
