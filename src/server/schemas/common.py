"""Unified API response wrappers."""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard envelope for all API responses."""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """Standard error payload."""

    code: int
    message: str
    detail: Optional[str] = None


def ok(data: Any = None, message: str = "ok") -> dict:
    """Build a success response dict."""
    return {"code": 0, "message": message, "data": data}


def fail(code: int, message: str, detail: Optional[str] = None) -> dict:
    """Build an error response dict."""
    return {"code": code, "message": message, "detail": detail}
