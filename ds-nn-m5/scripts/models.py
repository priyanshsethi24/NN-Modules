from dataclasses import dataclass
from typing import List

@dataclass
class TextElement:
    text: str
    font_size: float
    style: str

@dataclass
class PageContent:
    page_number: int
    elements: List[TextElement]

@dataclass
class FormatIssue:
    page: int
    text: str
    current_size: float
    expected_size: float
    style: str