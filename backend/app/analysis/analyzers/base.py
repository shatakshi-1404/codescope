from typing import Protocol

from app.analysis.config import Thresholds
from app.analysis.types import FileAnalysis


class LanguageAnalyzer(Protocol):
    """To add a language: implement this protocol and register it in registry.py."""

    language: str
    extensions: tuple[str, ...]

    def analyze(self, path: str, source: str, thresholds: Thresholds) -> FileAnalysis: ...
