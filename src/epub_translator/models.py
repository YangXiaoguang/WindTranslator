from dataclasses import dataclass, field
from typing import List


@dataclass
class ContentBlock:
    block_type: str  # h1, h2, h3, p
    text: str
    translated: str = ""


@dataclass
class Chapter:
    title: str
    blocks: List[ContentBlock] = field(default_factory=list)
