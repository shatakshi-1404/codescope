from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


@dataclass(frozen=True)
class Finding:
    """One quality issue OR one security finding. Language-agnostic."""

    rule_id: str
    file: str
    line: int
    category: str
    severity: Severity
    title: str
    description: str
    recommendation: str


@dataclass(frozen=True)
class FunctionMetrics:
    name: str
    line: int
    length: int
    param_count: int
    max_nesting: int
    branch_count: int
    cyclomatic: int
    body_hash: str | None = None  # used for exact-duplicate detection
    body_size: int = 0            # statements (Python) / non-empty lines (JS)


@dataclass(frozen=True)
class ClassInfo:
    name: str
    line: int


@dataclass(frozen=True)
class ImportInfo:
    name: str
    line: int


@dataclass
class FileMetrics:
    path: str
    language: str
    total_lines: int
    lines_of_code: int
    functions: list[FunctionMetrics] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    import_count: int = 0
    unused_imports: list[ImportInfo] = field(default_factory=list)
    parse_error: str | None = None

    @property
    def function_count(self) -> int:
        return len(self.functions)

    @property
    def class_count(self) -> int:
        return len(self.classes)

    @property
    def max_complexity(self) -> int:
        return max((f.cyclomatic for f in self.functions), default=0)

    @property
    def avg_complexity(self) -> float:
        if not self.functions:
            return 0.0
        return sum(f.cyclomatic for f in self.functions) / len(self.functions)


@dataclass
class FileAnalysis:
    metrics: FileMetrics
    issues: list[Finding] = field(default_factory=list)
    security: list[Finding] = field(default_factory=list)
