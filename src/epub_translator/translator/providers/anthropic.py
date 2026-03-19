import time
import logging

from .base import LLMProvider
from ...config import MAX_RETRIES

log = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError("需安装 anthropic 包：pip install anthropic")
        self.client = _anthropic.Anthropic(api_key=api_key)
        self.model = model
        # These errors are configuration mistakes — retrying them is pointless
        self._non_retryable = (
            _anthropic.AuthenticationError,
            _anthropic.PermissionDeniedError,
            _anthropic.NotFoundError,
            _anthropic.UnprocessableEntityError,
        )

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        for attempt in range(MAX_RETRIES):
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
                raise  # configuration errors — fail fast, no retry
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"Anthropic API 调用失败，已达最大重试次数（{MAX_RETRIES}）"
                    ) from e
                wait = 2 ** attempt
                log.warning("API错误，%ds后重试 (%d/%d): %s", wait, attempt + 1, MAX_RETRIES, e)
                time.sleep(wait)
