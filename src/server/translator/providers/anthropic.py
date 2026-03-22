"""Anthropic Claude provider."""

from __future__ import annotations

import time
import logging

from .base import BaseLLMProvider

log = logging.getLogger(__name__)

_MAX_RETRIES = 3


class AnthropicProvider(BaseLLMProvider):
    """Calls the Anthropic Messages API with retry logic."""

    def __init__(self, api_key: str, model: str) -> None:
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError("需安装 anthropic 包: pip install anthropic")
        self.client = _anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._non_retryable = (
            _anthropic.AuthenticationError,
            _anthropic.PermissionDeniedError,
            _anthropic.NotFoundError,
            _anthropic.UnprocessableEntityError,
        )

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Send a request to Claude and return the response text."""
        for attempt in range(_MAX_RETRIES):
            try:
                resp = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                if not resp.content:
                    raise RuntimeError("API 返回空内容列表")
                return resp.content[0].text.strip()
            except self._non_retryable:
                raise
            except Exception as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"Anthropic API 失败，已重试 {_MAX_RETRIES} 次"
                    ) from exc
                wait = 2 ** attempt
                log.warning(
                    "API 错误, %ds 后重试 (%d/%d): %s",
                    wait, attempt + 1, _MAX_RETRIES, exc,
                )
                time.sleep(wait)
        raise RuntimeError("unreachable")  # pragma: no cover
