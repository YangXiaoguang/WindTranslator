"""Configuration endpoints: list providers, test API key."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from ..schemas.common import ok
from ..schemas.translate import TestKeyRequest, TestKeyResponse
from ..translator.providers import get_provider

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])

_PROVIDERS = {
    "anthropic": {
        "name": "Anthropic",
        "models": ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        "requires_base_url": False,
    },
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini"],
        "requires_base_url": False,
    },
    "deepseek": {
        "name": "DeepSeek",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "requires_base_url": False,
    },
    "custom": {
        "name": "Custom (OpenAI-compatible)",
        "models": [],
        "requires_base_url": True,
    },
}


@router.get("/providers", summary="可用 provider 列表")
async def list_providers() -> dict:
    """Return all supported LLM providers and their config requirements."""
    return ok(_PROVIDERS)


@router.post("/test-key", summary="测试 API Key 连通性")
async def test_api_key(body: TestKeyRequest) -> dict:
    """Send a short test translation to verify the API key works."""
    try:
        provider = get_provider(
            provider=body.provider,
            api_key=body.api_key,
            model=body.model,
            base_url=body.base_url,
        )
        result = provider.complete(
            system="Translate to Chinese.",
            user="Hello, world!",
            max_tokens=100,
        )
        return ok(
            TestKeyResponse(success=True, message=f"连接成功: {result[:50]}").model_dump()
        )
    except Exception as exc:
        log.warning("API Key 测试失败: %s", exc)
        return ok(
            TestKeyResponse(success=False, message=f"连接失败: {exc}").model_dump()
        )
