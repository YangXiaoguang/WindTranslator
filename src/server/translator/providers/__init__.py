"""LLM provider registry — string name → provider instance."""

from __future__ import annotations

from .base import BaseLLMProvider
from .anthropic import AnthropicProvider
from .openai_compat import OpenAICompatProvider

__all__ = [
    "BaseLLMProvider",
    "AnthropicProvider",
    "OpenAICompatProvider",
    "get_provider",
]

_OPENAI_COMPAT = {"openai", "deepseek", "custom"}


def get_provider(
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> BaseLLMProvider:
    """Factory: return the correct provider by string name."""
    name = provider.lower()
    if name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    if name in _OPENAI_COMPAT:
        return OpenAICompatProvider(
            api_key=api_key, model=model,
            base_url=base_url, provider=name,
        )
    supported = ", ".join(sorted({"anthropic"} | _OPENAI_COMPAT))
    raise ValueError(f"未知 provider: {provider!r}，支持: {supported}")
