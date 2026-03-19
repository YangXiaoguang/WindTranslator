from abc import ABC, abstractmethod
from typing import List

from ..models import Chapter


class AbstractParser(ABC):
    @abstractmethod
    def get_title(self) -> str: ...

    @abstractmethod
    def get_chapters(self) -> List[Chapter]: ...
