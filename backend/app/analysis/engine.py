import os
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.analysis.analyzers.registry import get_analyzer
from app.analysis.config import DEFAULT_LIMITS, DEFAULT_THRESHOLDS, EngineLimits, Thresholds
from app.analysis.metrics.scoring import ScoreResult, compute_score
from app.analysis.quality.rules import check_duplicates
from app.analysis.types import SEVERITY_RANK, FileMetrics, Finding

ProgressCallback = Callable[[int, int], None]  # (files_done, files_total)


@dataclass
class AnalysisResult:
    files: list[FileMetrics]
    issues: list[Finding]
    security_findings: list[Finding]
    score: ScoreResult
    skipped_files: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def files_analyzed(self) -> int:
        return len(self.files)

    @property
    def lines_analyzed(self) -> int:
        return sum(f.lines_of_code for f in self.files)

    @property
    def function_count(self) -> int:
        return sum(f.function_count for f in self.files)

    @property
    def class_count(self) -> int:
        return sum(f.class_count for f in self.files)

    @property
    def primary_language(self) -> str | None:
        loc_by_language: Counter[str] = Counter()
        for f in self.files:
            loc_by_language[f.language] += f.lines_of_code
        return loc_by_language.most_common(1)[0][0] if loc_by_language else None


def discover_files(root: Path, limits: EngineLimits) -> tuple[list[Path], int]:
    """
    Finds supported source files. Safety rules:
    - symlinks are never followed (a hostile repo could point one at /etc/passwd)
    - hidden folders, dependency folders and build output are skipped
    - oversized files and files beyond the max-files limit are skipped
    """
    found: list[Path] = []
    skipped = 0

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in limits.ignored_dirs
            and not os.path.islink(os.path.join(dirpath, d))
        )
        for filename in sorted(filenames):
            if get_analyzer(filename) is None:
                continue
            full = os.path.join(dirpath, filename)
            if os.path.islink(full):
                skipped += 1
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                skipped += 1
                continue
            if size > limits.max_file_bytes or len(found) >= limits.max_files:
                skipped += 1
                continue
            found.append(Path(full))

    return found, skipped


def analyze_directory(
    root: str | Path,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
    limits: EngineLimits = DEFAULT_LIMITS,
    on_progress: ProgressCallback | None = None,
) -> AnalysisResult:
    root = Path(root).resolve()
    paths, skipped = discover_files(root, limits)

    all_metrics: list[FileMetrics] = []
    issues: list[Finding] = []
    security: list[Finding] = []
    warnings: list[str] = []

    for index, path in enumerate(paths, start=1):
        rel = path.relative_to(root).as_posix()
        analyzer = get_analyzer(rel)
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            file_analysis = analyzer.analyze(rel, source, thresholds)
        except Exception as exc:  # noqa: BLE001
            # One unreadable/pathological file must never abort the whole analysis.
            warnings.append(f"{rel}: could not be analyzed ({type(exc).__name__})")
            skipped += 1
            continue

        if file_analysis.metrics.parse_error:
            warnings.append(f"{rel}: {file_analysis.metrics.parse_error}")
        all_metrics.append(file_analysis.metrics)
        issues.extend(file_analysis.issues)
        security.extend(file_analysis.security)

        if on_progress:
            on_progress(index, len(paths))

    issues.extend(check_duplicates(all_metrics, thresholds))

    # Deterministic ordering: worst first, then by location.
    issues.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.file, f.line, f.rule_id))
    security.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.file, f.line, f.rule_id))

    return AnalysisResult(
        files=all_metrics,
        issues=issues,
        security_findings=security,
        score=compute_score(all_metrics, issues, security),
        skipped_files=skipped,
        warnings=warnings,
    )
