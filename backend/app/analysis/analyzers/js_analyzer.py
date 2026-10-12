from app.analysis.config import Thresholds
from app.analysis.parsers.js_parser import parse_js
from app.analysis.quality import rules as quality_rules
from app.analysis.security import rules as security_rules
from app.analysis.types import FileAnalysis


class JsTsAnalyzer:
    """One implementation, registered twice (javascript / typescript)."""

    def __init__(self, language: str, extensions: tuple[str, ...]):
        self.language = language
        self.extensions = extensions

    def analyze(self, path: str, source: str, thresholds: Thresholds) -> FileAnalysis:
        metrics = parse_js(path, source, self.language)
        issues = quality_rules.check_file(metrics, thresholds)
        security = security_rules.scan_javascript(path, source)
        security.extend(security_rules.scan_secrets(path, source, self.language))
        return FileAnalysis(metrics=metrics, issues=issues, security=security)
