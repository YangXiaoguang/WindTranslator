"""OpenAI-compatible provider (OpenAI, DeepSeek, custom endpoints)."""

from __future__ import annotations

import time
import logging

from .base import BaseLLMProvider

log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class OpenAICompatProvider(BaseLLMProvider):
    """Calls any OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        provider: str = "openai",
    ) -> None:
        try:
            import openai as _openai
        except ImportError:
            raise ImportError("需安装 openai 包: pip install openai")
        url = base_url or (_DEEPSEEK_BASE_URL if provider == "deepseek" else None)
        kwargs: dict = {"api_key": api_key}
        if url:
            kwargs["base_url"] = url
        self.client = _openai.OpenAI(**kwargs)
        self.model = model
        self._non_retryable = (
            _openai.AuthenticationError,
            _openai.PermissionDeniedError,
            _openai.NotFoundError,
        )

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Send a chat completion request and return the response text."""
        for attempt in range(_MAX_RETRIES):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                if not resp.choices:
                    raise RuntimeError("API 返回空 choices 列表")
                content = resp.choices[0].message.content
                if content is None:
                    raise RuntimeError("API 返回 null content")
                return content.strip()
            except self._non_retryable:
                raise
            except Exception as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"OpenAI API 失败，已重试 {_MAX_RETRIES} 次"
                    ) from exc
                wait = 2 ** attempt
                log.warning(
                    "API 错误, %ds 后重试 (%d/%d): %s",
                    wait, attempt + 1, _MAX_RETRIES, exc,
                )
                time.sleep(wait)
        raise RuntimeError("unreachable")  # pragma: no cover
