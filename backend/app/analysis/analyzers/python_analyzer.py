from app.analysis.config import Thresholds
from app.analysis.parsers.python_parser import parse_python
from app.analysis.quality import rules as quality_rules
from app.analysis.security import rules as security_rules
from app.analysis.types import FileAnalysis


class PythonAnalyzer:
    language = "python"
    extensions = (".py",)

    def analyze(self, path: str, source: str, thresholds: Thresholds) -> FileAnalysis:
        metrics, tree = parse_python(path, source)
        issues = quality_rules.check_file(metrics, thresholds)

        security = []
        if tree is not None:
            security.extend(security_rules.scan_python(path, tree))
        security.extend(security_rules.scan_secrets(path, source, "python"))

        return FileAnalysis(metrics=metrics, issues=issues, security=security)
