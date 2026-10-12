from dataclasses import dataclass, field

from app.analysis.types import FileMetrics, Finding, Severity

# ---------------------------------------------------------------- the formula
# Each finding costs points by severity:
SEVERITY_POINTS = {
    Severity.LOW: 1.0,
    Severity.MEDIUM: 3.0,
    Severity.HIGH: 6.0,
    Severity.CRITICAL: 12.0,
}
# Penalty = factor * points / KLOC  (KLOC = thousand lines of code, minimum 1)
# so a big repository is not punished just for being big.
ISSUE_PENALTY_PER_KLOC = 3.0
SECURITY_PENALTY_PER_KLOC = 4.0
# Any CRITICAL security finding caps the security score:
CRITICAL_SECURITY_CAP = 60.0
# Complexity also looks at the average cyclomatic complexity per function:
COMPLEXITY_BASELINE = 5.0
COMPLEXITY_SLOPE = 4.0
COMPLEXITY_MAX_PENALTY = 30.0

CODE_QUALITY_CATEGORIES = frozenset({"naming", "unused-code", "duplication"})
MAINTAINABILITY_CATEGORIES = frozenset({"maintainability"})
COMPLEXITY_CATEGORIES = frozenset({"complexity"})


@dataclass(frozen=True)
class ScoreWeights:
    code_quality: float = 0.25
    maintainability: float = 0.25
    complexity: float = 0.25
    security: float = 0.25


@dataclass(frozen=True)
class ScoreResult:
    overall: float
    code_quality: float
    maintainability: float
    complexity: float
    security: float
    details: dict[str, float] = field(default_factory=dict)  # shown in "How is this calculated?"


def _points(findings: list[Finding], categories: frozenset[str] | None = None) -> float:
    return sum(
        SEVERITY_POINTS[f.severity]
        for f in findings
        if categories is None or f.category in categories
    )


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def compute_score(
    files: list[FileMetrics],
    issues: list[Finding],
    security_findings: list[Finding],
    weights: ScoreWeights = ScoreWeights(),
) -> ScoreResult:
    total_loc = sum(f.lines_of_code for f in files)
    kloc = max(total_loc / 1000, 1.0)

    all_functions = [fn for f in files for fn in f.functions]
    avg_cyclomatic = (
        sum(fn.cyclomatic for fn in all_functions) / len(all_functions) if all_functions else 0.0
    )

    quality_pts = _points(issues, CODE_QUALITY_CATEGORIES)
    maint_pts = _points(issues, MAINTAINABILITY_CATEGORIES)
    complexity_pts = _points(issues, COMPLEXITY_CATEGORIES)
    security_pts = _points(security_findings)

    code_quality = _clamp(100 - ISSUE_PENALTY_PER_KLOC * quality_pts / kloc)
    maintainability = _clamp(100 - ISSUE_PENALTY_PER_KLOC * maint_pts / kloc)

    avg_penalty = min(
        COMPLEXITY_MAX_PENALTY, max(0.0, avg_cyclomatic - COMPLEXITY_BASELINE) * COMPLEXITY_SLOPE
    )
    complexity = _clamp(100 - ISSUE_PENALTY_PER_KLOC * complexity_pts / kloc - avg_penalty)

    security = 100 - SECURITY_PENALTY_PER_KLOC * security_pts / kloc
    if any(f.severity == Severity.CRITICAL for f in security_findings):
        security = min(security, CRITICAL_SECURITY_CAP)
    security = _clamp(security)

    overall = _clamp(
        code_quality * weights.code_quality
        + maintainability * weights.maintainability
        + complexity * weights.complexity
        + security * weights.security
    )

    return ScoreResult(
        overall=overall,
        code_quality=code_quality,
        maintainability=maintainability,
        complexity=complexity,
        security=security,
        details={
            "kloc": round(kloc, 2),
            "avg_cyclomatic": round(avg_cyclomatic, 2),
            "quality_points": quality_pts,
            "maintainability_points": maint_pts,
            "complexity_points": complexity_pts,
            "security_points": security_pts,
        },
    )
