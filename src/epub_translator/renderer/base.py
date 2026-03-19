from abc import ABC, abstractmethod
from typing import List

from ..models import Chapter


class AbstractRenderer(ABC):
    @abstractmethod
    def render(self, chapters: List[Chapter], output_path: str) -> None: ...
