import os

from app.analysis.analyzers.base import LanguageAnalyzer
from app.analysis.analyzers.js_analyzer import JsTsAnalyzer
from app.analysis.analyzers.python_analyzer import PythonAnalyzer

_ANALYZERS: list[LanguageAnalyzer] = [
    PythonAnalyzer(),
    JsTsAnalyzer("javascript", (".js", ".jsx", ".mjs", ".cjs")),
    JsTsAnalyzer("typescript", (".ts", ".tsx")),
]

_BY_EXTENSION = {ext: a for a in _ANALYZERS for ext in a.extensions}
_SKIP_SUFFIXES = (".min.js", ".min.mjs", ".d.ts")


def get_analyzer(path: str) -> LanguageAnalyzer | None:
    lowered = path.lower()
    if lowered.endswith(_SKIP_SUFFIXES):
        return None
    return _BY_EXTENSION.get(os.path.splitext(lowered)[1])
