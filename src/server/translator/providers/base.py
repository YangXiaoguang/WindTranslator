"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Single responsibility: make one LLM API call and return text."""

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Send a prompt and return the model's text response."""
        ...
