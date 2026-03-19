import time
import logging
from typing import Optional

from .base import LLMProvider
from ...config import MAX_RETRIES

log = logging.getLogger(__name__)

_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class OpenAICompatProvider(LLMProvider):
    """Handles OpenAI, DeepSeek, and any other OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        provider: str = "openai",
    ):
        try:
            import openai as _openai
        except ImportError:
            raise ImportError("需安装 openai 包：pip install openai")
        url = base_url or (_DEEPSEEK_BASE_URL if provider == "deepseek" else None)
        kwargs = {"api_key": api_key}
        if url:
            kwargs["base_url"] = url
        self.client = _openai.OpenAI(**kwargs)
        self.model = model
        # These errors are configuration mistakes — retrying them is pointless
        self._non_retryable = (
            _openai.AuthenticationError,
            _openai.PermissionDeniedError,
            _openai.NotFoundError,
        )

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        for attempt in range(MAX_RETRIES):
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
                raise  # configuration errors — fail fast, no retry
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"OpenAI API 调用失败，已达最大重试次数（{MAX_RETRIES}）"
                    ) from e
                wait = 2 ** attempt
                log.warning("API错误，%ds后重试 (%d/%d): %s", wait, attempt + 1, MAX_RETRIES, e)
                time.sleep(wait)
