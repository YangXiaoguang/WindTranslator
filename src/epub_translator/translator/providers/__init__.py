from .base import LLMProvider
from .anthropic import AnthropicProvider
from .openai_compat import OpenAICompatProvider
from ...config import TranslatorConfig

__all__ = ["LLMProvider", "AnthropicProvider", "OpenAICompatProvider", "get_provider"]

_OPENAI_COMPAT_PROVIDERS = {"openai", "deepseek", "custom"}


def get_provider(cfg: TranslatorConfig) -> LLMProvider:
    """Factory: return the right LLMProvider for the given config."""
    provider = cfg.provider.lower()
    if provider == "anthropic":
        return AnthropicProvider(api_key=cfg.api_key, model=cfg.model)
    if provider in _OPENAI_COMPAT_PROVIDERS:
        return OpenAICompatProvider(
            api_key=cfg.api_key,
            model=cfg.model,
            base_url=cfg.base_url,
            provider=provider,
        )
    raise ValueError(
        f"未知的 provider: {cfg.provider!r}，"
        f"支持: anthropic, openai, deepseek, custom"
    )
