from dataclasses import dataclass, field


@dataclass(frozen=True)
class SummaryInput:
    repo_name: str
    overall: float
    code_quality: float
    maintainability: float
    complexity: float
    security: float
    files_analyzed: int
    lines_analyzed: int
    issue_severity: dict[str, int]
    security_severity: dict[str, int]
    issue_categories: dict[str, int]
    top_files: list[tuple[str, int]] = field(default_factory=list)
    previous_overall: float | None = None


_DIMENSIONS = (
    ("code quality", "code_quality"),
    ("maintainability", "maintainability"),
    ("complexity", "complexity"),
    ("security", "security"),
)

_CATEGORY_ADVICE = {
    "complexity": "Reduce complexity: use early returns and split heavily branching functions into smaller ones.",
    "maintainability": "Break up long functions, long parameter lists and oversized files into smaller units.",
    "duplication": "Extract duplicated function bodies into shared helpers.",
    "unused-code": "Remove unused imports to keep modules tidy.",
    "naming": "Rename vaguely or inconsistently named functions and classes.",
}


def score_label(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 80:
        return "good"
    if score >= 65:
        return "fair"
    if score >= 50:
        return "needs attention"
    return "poor"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def generate_summary(inp: SummaryInput) -> str:
    parts = [
        f"{inp.repo_name} scored {inp.overall:.0f}/100 ({score_label(inp.overall)}) "
        f"across {inp.files_analyzed:,} files and {inp.lines_analyzed:,} lines of code."
    ]

    dims = sorted(((label, getattr(inp, attr)) for label, attr in _DIMENSIONS), key=lambda d: d[1])
    weakest, strongest = dims[0], dims[-1]
    if weakest[1] != strongest[1]:
        parts.append(
            f"Its strongest area is {strongest[0]} ({strongest[1]:.0f}) "
            f"and its weakest is {weakest[0]} ({weakest[1]:.0f})."
        )

    total = sum(inp.issue_severity.values())
    if total == 0:
        parts.append("No code quality issues were detected.")
    else:
        serious = inp.issue_severity.get("HIGH", 0) + inp.issue_severity.get("CRITICAL", 0)
        top_category = max(inp.issue_categories.items(), key=lambda kv: (kv[1], kv[0]))[0]
        verb = "was" if total == 1 else "were"
        parts.append(
            f"{total} quality {'issue' if total == 1 else 'issues'} {verb} found, "
            f"{serious} of them high or critical severity; most fall under {top_category}."
        )
        if inp.top_files and inp.top_files[0][1] >= 3:
            path, count = inp.top_files[0]
            parts.append(f"Issues are concentrated in {path} ({count} issues).")

    sec_total = sum(inp.security_severity.values())
    if sec_total == 0:
        parts.append(
            "The static security checks found nothing to report (this is not a full security audit)."
        )
    else:
        critical = inp.security_severity.get("CRITICAL", 0)
        parts.append(
            f"The static security checks flagged {_plural(sec_total, 'finding')}, "
            f"{critical} critical."
        )

    if inp.previous_overall is not None:
        diff = inp.overall - inp.previous_overall
        if abs(diff) < 0.5:
            parts.append("The overall score is unchanged since the previous analysis.")
        else:
            direction = "improved" if diff > 0 else "declined"
            parts.append(
                f"Since the previous analysis the overall score {direction} by {abs(diff):.1f} points."
            )

    return " ".join(parts)


def improvement_plan(
    issue_severity: dict[str, int],
    security_severity: dict[str, int],
    issue_categories: dict[str, int],
    max_steps: int = 4,
) -> list[str]:
    """Ordered, deterministic next steps derived from the findings."""
    steps: list[str] = []

    critical = security_severity.get("CRITICAL", 0)
    if critical:
        steps.append(
            f"Fix the {_plural(critical, 'critical security finding')} first; "
            "if any are exposed secrets, rotate them."
        )
    high_sec = security_severity.get("HIGH", 0)
    if high_sec:
        steps.append(f"Review the {_plural(high_sec, 'high-severity security finding')}.")
    serious = issue_severity.get("HIGH", 0) + issue_severity.get("CRITICAL", 0)
    if serious:
        steps.append(f"Address the {_plural(serious, 'high-severity quality issue')}.")

    for category, _count in sorted(issue_categories.items(), key=lambda kv: (-kv[1], kv[0])):
        advice = _CATEGORY_ADVICE.get(category)
        if advice and advice not in steps:
            steps.append(advice)

    if not steps:
        steps.append("Keep the current standards and re-run the analysis after major changes.")
    return steps[:max_steps]
