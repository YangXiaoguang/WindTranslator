from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Single responsibility: make one LLM API call and return the text."""

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str: ...
