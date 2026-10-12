import re
from collections import defaultdict

from app.analysis.config import Thresholds
from app.analysis.types import FileMetrics, Finding, FunctionMetrics, Severity

_VAGUE_NAMES = frozenset(
    {"foo", "bar", "baz", "temp", "tmp", "stuff", "thing", "things",
     "doit", "do_it", "asdf", "xxx", "test1", "func1"}
)
_FRAMEWORK_NAMES = frozenset(
    {"setUp", "tearDown", "setUpClass", "tearDownClass", "setUpModule",
     "tearDownModule", "asyncSetUp", "asyncTearDown"}
)


def severity_by_ratio(value: float, threshold: float) -> Severity | None:
    """
    Deterministic severity scale, the same for every threshold-based rule:
        value <= threshold           -> no finding
        up to 1.5x the threshold     -> LOW
        1.5x to under 2.5x           -> MEDIUM
        2.5x and above               -> HIGH
    (CRITICAL is reserved for security findings.)
    """
    if value <= threshold:
        return None
    ratio = value / threshold
    if ratio < 1.5:
        return Severity.LOW
    if ratio < 2.5:
        return Severity.MEDIUM
    return Severity.HIGH


def _function_findings(path: str, fn: FunctionMetrics, t: Thresholds) -> list[Finding]:
    checks = (
        ("QUAL-001", "maintainability", "Function is too long", fn.length, t.max_function_length,
         "lines", "Split it into smaller functions that each do one thing."),
        ("QUAL-002", "maintainability", "Too many parameters", fn.param_count, t.max_parameters,
         "parameters", "Group related parameters into an object/dataclass, or split the function."),
        ("QUAL-003", "complexity", "Excessive nesting", fn.max_nesting, t.max_nesting_depth,
         "levels of nesting", "Use early returns (guard clauses) or extract inner blocks into helpers."),
        ("QUAL-004", "complexity", "Too many branches", fn.branch_count, t.max_branches,
         "branches", "Replace long if/elif chains with lookup tables or smaller functions."),
        ("QUAL-005", "complexity", "High cyclomatic complexity", fn.cyclomatic, t.max_cyclomatic,
         "independent paths (cyclomatic complexity)",
         "Break it into smaller units, each with a single responsibility."),
    )
    findings = []
    for rule_id, category, title, value, limit, unit, recommendation in checks:
        severity = severity_by_ratio(value, limit)
        if severity:
            findings.append(
                Finding(
                    rule_id=rule_id, file=path, line=fn.line, category=category,
                    severity=severity, title=f"{title}: {fn.name}",
                    description=f"`{fn.name}` has {value} {unit} (threshold: {limit}).",
                    recommendation=recommendation,
                )
            )
    return findings


def _naming_findings(metrics: FileMetrics, fn: FunctionMetrics) -> list[Finding]:
    base = fn.name.rsplit(".", 1)[-1]
    if base == "<anonymous>" or (base.startswith("__") and base.endswith("__")):
        return []

    out = []
    stripped = base.lstrip("_")
    if base.lower() in _VAGUE_NAMES or (len(stripped) == 1 and base != "_"):
        out.append(
            Finding(
                "QUAL-009", metrics.path, fn.line, "naming", Severity.LOW,
                f"Vague function name: {base}",
                f"`{base}` does not describe what the function does.",
                "Rename it to a verb phrase that states its purpose (e.g. `parse_config`).",
            )
        )
    if (
        metrics.language == "python"
        and base not in _FRAMEWORK_NAMES
        and not base.startswith(("visit_", "do_"))
        and re.search(r"[a-z][A-Z]", stripped)
        and not stripped.isupper()
    ):
        out.append(
            Finding(
                "QUAL-010", metrics.path, fn.line, "naming", Severity.LOW,
                f"Function name is not snake_case: {base}",
                f"`{base}` uses camelCase, but Python (PEP 8) uses snake_case for functions.",
                "Rename it to snake_case.",
            )
        )
    return out


def check_file(metrics: FileMetrics, t: Thresholds) -> list[Finding]:
    """All per-file rules. Pure function: metrics in, findings out."""
    findings: list[Finding] = []

    for fn in metrics.functions:
        findings.extend(_function_findings(metrics.path, fn, t))
        findings.extend(_naming_findings(metrics, fn))

    severity = severity_by_ratio(metrics.total_lines, t.max_file_lines)
    if severity:
        findings.append(
            Finding(
                "QUAL-006", metrics.path, 1, "maintainability", severity, "File is too large",
                f"The file has {metrics.total_lines} lines (threshold: {t.max_file_lines}).",
                "Split it into smaller modules grouped by responsibility.",
            )
        )

    for imp in metrics.unused_imports:
        findings.append(
            Finding(
                "QUAL-007", metrics.path, imp.line, "unused-code", Severity.LOW,
                f"Unused import: {imp.name}",
                f"`{imp.name}` is imported but never used in this file.",
                "Remove the import.",
            )
        )

    if metrics.language == "python":
        for cls in metrics.classes:
            if not re.fullmatch(r"_*[A-Z][A-Za-z0-9]*", cls.name):
                findings.append(
                    Finding(
                        "QUAL-011", metrics.path, cls.line, "naming", Severity.LOW,
                        f"Class name is not CapWords: {cls.name}",
                        f"`{cls.name}` does not follow the PEP 8 CapWords convention.",
                        "Rename the class using CapWords (e.g. `UserService`).",
                    )
                )
    return findings


def check_duplicates(all_metrics: list[FileMetrics], t: Thresholds) -> list[Finding]:
    """
    Cross-file rule: functions whose bodies are structurally IDENTICAL
    (same hash). The first occurrence is the original; later ones are flagged.
    """
    groups: dict[str, list[tuple[str, FunctionMetrics]]] = defaultdict(list)
    for m in all_metrics:
        for fn in m.functions:
            if fn.body_hash and fn.body_size >= t.min_duplicate_size:
                groups[fn.body_hash].append((m.path, fn))

    findings: list[Finding] = []
    for occurrences in groups.values():
        if len(occurrences) < 2:
            continue
        occurrences.sort(key=lambda o: (o[0], o[1].line))
        orig_path, orig_fn = occurrences[0]
        for path, fn in occurrences[1:]:
            findings.append(
                Finding(
                    "QUAL-008", path, fn.line, "duplication", Severity.MEDIUM,
                    f"Duplicate function body: {fn.name}",
                    f"`{fn.name}` has exactly the same body as `{orig_fn.name}` "
                    f"in {orig_path}:{orig_fn.line}.",
                    "Extract the shared logic into one function and reuse it.",
                )
            )
    return findings
