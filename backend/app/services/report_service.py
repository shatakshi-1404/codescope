from collections import Counter, defaultdict
from typing import NamedTuple

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.intelligence.clustering import cluster_texts, top_terms
from app.intelligence.summary import improvement_plan
from app.models import (
    Analysis,
    AnalysisFile,
    AnalysisStatus,
    Issue,
    IssueStatus,
    QualityMetric,
    SecurityFinding,
    Severity,
)
from app.schemas.analysis import AnalysisResponse, ScoresResponse
from app.schemas.report import (
    ArchitectureSection,
    ClusterResponse,
    ComplexityFile,
    ComplexitySection,
    DirectoryStat,
    DistributionBucket,
    FilePage,
    FileResponse,
    HistoryPoint,
    InsightsResponse,
    LanguageStat,
    LargeFile,
    OverviewCards,
    QualitySection,
    ReportResponse,
    RuleCount,
    SecuritySection,
)

SEV_KEYS = [s.value for s in Severity]
STATUS_KEYS = [s.value for s in IssueStatus]
SEV_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
MAX_CLUSTERED = 2000

SCORE_EXPLANATION = (
    "Each finding costs points by severity (LOW 1, MEDIUM 3, HIGH 6, CRITICAL 12). "
    "Penalties are scaled per 1,000 lines of code so large repositories are not punished for size. "
    "Complexity also considers the average cyclomatic complexity per function. "
    "A critical security finding caps the Security score at 60. "
    "The overall score is the average of the four dimensions. "
    "This is a transparent heuristic, not a scientific measurement."
)

RULE_NAMES = {
    "QUAL-001": "Long function", "QUAL-002": "Too many parameters", "QUAL-003": "Deep nesting",
    "QUAL-004": "Too many branches", "QUAL-005": "High cyclomatic complexity",
    "QUAL-006": "Large file", "QUAL-007": "Unused import", "QUAL-008": "Duplicate function body",
    "QUAL-009": "Vague function name", "QUAL-010": "Non-snake_case function",
    "QUAL-011": "Non-CapWords class",
    "SEC-EVAL": "Dynamic code execution (eval)", "SEC-EXEC": "Dynamic code execution (exec)",
    "SEC-SUBPROCESS-SHELL": "Shell command execution", "SEC-SQL-INJECTION": "SQL built from strings",
    "SEC-WEAK-PASSWORD-HASH": "Weak password hashing", "SEC-DESERIALIZATION": "Unsafe deserialization",
    "SEC-TLS-VERIFY": "TLS verification disabled", "SEC-DOM-XSS": "Possible DOM XSS sink",
    "SEC-COMMAND-INJECTION": "Shell command from dynamic input",
    "SEC-SECRET-TOKEN": "Known secret token format", "SEC-HARDCODED-PASSWORD": "Hardcoded password",
    "SEC-HARDCODED-API-KEY": "Hardcoded API key", "SEC-HIGH-ENTROPY": "High-entropy string",
}

_BUCKETS = [("1-5", 1, 5), ("6-10", 6, 10), ("11-15", 11, 15), ("16-25", 16, 25), ("26+", 26, 10**9)]


def count_by(db: Session, column, *conditions) -> dict[str, int]:
    rows = db.execute(select(column, func.count()).where(*conditions).group_by(column)).all()
    return {getattr(key, "value", key): count for key, count in rows}


def full_counts(counts: dict[str, int], keys: list[str]) -> dict[str, int]:
    return {k: counts.get(k, 0) for k in keys}


def _require_completed(analysis: Analysis) -> None:
    if analysis.status != AnalysisStatus.COMPLETED:
        raise ConflictError("This analysis has not completed yet.")


def _rule_counts(db: Session, model, analysis_id: int, limit: int = 8) -> list[RuleCount]:
    rows = db.execute(
        select(model.rule_id, func.count())
        .where(model.analysis_id == analysis_id)
        .group_by(model.rule_id)
        .order_by(func.count().desc(), model.rule_id)
        .limit(limit)
    ).all()
    return [RuleCount(rule_id=r, name=RULE_NAMES.get(r, r), count=c) for r, c in rows]


# =================================================================== report
def build_report(db: Session, analysis: Analysis) -> ReportResponse:
    _require_completed(analysis)
    aid = analysis.id
    metrics = analysis.metrics
    files = list(db.scalars(select(AnalysisFile).where(AnalysisFile.analysis_id == aid)))

    issues_by_severity = full_counts(count_by(db, Issue.severity, Issue.analysis_id == aid), SEV_KEYS)
    issues_by_status = full_counts(count_by(db, Issue.status, Issue.analysis_id == aid), STATUS_KEYS)
    issues_by_category = dict(
        sorted(count_by(db, Issue.category, Issue.analysis_id == aid).items(), key=lambda kv: -kv[1])
    )
    security_by_severity = full_counts(
        count_by(db, SecurityFinding.severity, SecurityFinding.analysis_id == aid), SEV_KEYS
    )

    # ---- complexity
    with_functions = [f for f in files if f.function_count > 0]
    distribution = [
        DistributionBucket(
            label=label,
            files=sum(1 for f in with_functions if low <= f.max_complexity <= high),
        )
        for label, low, high in _BUCKETS
    ]
    most_complex = sorted(with_functions, key=lambda f: (-f.max_complexity, f.path))[:10]

    # ---- architecture
    languages: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    directories: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for f in files:
        languages[f.language][0] += 1
        languages[f.language][1] += f.lines_of_code
        top = f.path.split("/")[0] if "/" in f.path else "(root)"
        directories[top][0] += 1
        directories[top][1] += f.lines_of_code

    largest = sorted(files, key=lambda f: (-f.lines_of_code, f.path))[:10]

    return ReportResponse(
        analysis=AnalysisResponse.from_model(analysis),
        overview=OverviewCards(
            files_analyzed=analysis.files_analyzed,
            lines_analyzed=analysis.lines_analyzed,
            functions=analysis.function_count,
            classes=analysis.class_count,
            issues=sum(issues_by_severity.values()),
            open_issues=issues_by_status["OPEN"],
            security_findings=sum(security_by_severity.values()),
        ),
        scores=(
            ScoresResponse(
                overall=metrics.overall_score,
                code_quality=metrics.code_quality_score,
                maintainability=metrics.maintainability_score,
                complexity=metrics.complexity_score,
                security=metrics.security_score,
            )
            if metrics
            else None
        ),
        score_explanation=SCORE_EXPLANATION,
        quality=QualitySection(
            issues_by_severity=issues_by_severity,
            issues_by_category=issues_by_category,
            issues_by_status=issues_by_status,
            top_rules=_rule_counts(db, Issue, aid),
        ),
        complexity=ComplexitySection(
            avg_cyclomatic=round(metrics.avg_complexity, 2) if metrics else 0.0,
            max_cyclomatic=max((f.max_complexity for f in files), default=0),
            distribution=distribution,
            most_complex_files=[
                ComplexityFile(
                    path=f.path,
                    max_complexity=f.max_complexity,
                    avg_complexity=f.avg_complexity,
                    functions=f.function_count,
                )
                for f in most_complex
            ],
        ),
        security=SecuritySection(
            total=sum(security_by_severity.values()),
            by_severity=security_by_severity,
            by_rule=_rule_counts(db, SecurityFinding, aid),
        ),
        architecture=ArchitectureSection(
            languages=[
                LanguageStat(language=k, files=v[0], lines=v[1])
                for k, v in sorted(languages.items(), key=lambda kv: -kv[1][1])
            ],
            directories=[
                DirectoryStat(name=k, files=v[0], lines=v[1])
                for k, v in sorted(directories.items(), key=lambda kv: -kv[1][1])[:12]
            ],
            largest_files=[
                LargeFile(path=f.path, lines_of_code=f.lines_of_code, functions=f.function_count)
                for f in largest
            ],
        ),
        ai_summary=analysis.ai_summary,
    )


# ==================================================================== files
_FILE_SORTS = {
    "path": AnalysisFile.path,
    "lines": AnalysisFile.lines_of_code,
    "complexity": AnalysisFile.max_complexity,
    "functions": AnalysisFile.function_count,
}


def list_files(
    db: Session, analysis: Analysis, *, sort: str, descending: bool, limit: int, offset: int
) -> FilePage:
    _require_completed(analysis)
    aid = analysis.id
    column = _FILE_SORTS[sort]
    order = column.desc() if descending else column.asc()

    total = db.scalar(select(func.count()).select_from(AnalysisFile).where(AnalysisFile.analysis_id == aid)) or 0
    rows = list(
        db.scalars(
            select(AnalysisFile)
            .where(AnalysisFile.analysis_id == aid)
            .order_by(order, AnalysisFile.path)
            .limit(limit)
            .offset(offset)
        )
    )
    paths = [r.path for r in rows]
    issue_counts = (
        dict(
            db.execute(
                select(Issue.file, func.count())
                .where(Issue.analysis_id == aid, Issue.file.in_(paths))
                .group_by(Issue.file)
            ).all()
        )
        if paths
        else {}
    )
    return FilePage(
        items=[
            FileResponse(
                path=r.path,
                language=r.language,
                lines_of_code=r.lines_of_code,
                function_count=r.function_count,
                class_count=r.class_count,
                import_count=r.import_count,
                max_complexity=r.max_complexity,
                avg_complexity=r.avg_complexity,
                issue_count=issue_counts.get(r.path, 0),
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# ================================================================== history
def repository_history(db: Session, repository_id: int, limit: int = 50) -> list[HistoryPoint]:
    """Completed analyses of a repository, oldest first, ready for line charts."""
    seq = func.row_number().over(order_by=Analysis.id).label("seq")
    numbered = (
        select(Analysis.id.label("aid"), seq)
        .where(Analysis.repository_id == repository_id, Analysis.status == AnalysisStatus.COMPLETED)
        .subquery()
    )
    rows = db.execute(
        select(Analysis, QualityMetric, numbered.c.seq)
        .join(numbered, numbered.c.aid == Analysis.id)
        .join(QualityMetric, QualityMetric.analysis_id == Analysis.id)
        .order_by(Analysis.id.desc())
        .limit(limit)
    ).all()

    return [
        HistoryPoint(
            analysis_id=a.id,
            number=number,
            date=a.completed_at or a.created_at,
            branch=a.branch,
            commit_sha=a.commit_sha,
            overall=m.overall_score,
            code_quality=m.code_quality_score,
            maintainability=m.maintainability_score,
            complexity=m.complexity_score,
            security=m.security_score,
            issue_count=m.issue_count,
            security_finding_count=m.security_finding_count,
            avg_complexity=m.avg_complexity,
        )
        for a, m, number in reversed(rows)
    ]


# ================================================================= insights
class _Item(NamedTuple):
    id: int
    rule_id: str
    label: str
    description: str
    severity: str
    file: str


def _clusterize(items: list[_Item]) -> list[ClusterResponse]:
    if not items:
        return []
    clusters = []
    for group in cluster_texts([i.description for i in items]):
        members = [items[idx] for idx in group]
        labels = Counter(m.label for m in members).most_common(2)
        clusters.append(
            ClusterResponse(
                label=" / ".join(label for label, _ in labels),
                size=len(members),
                highest_severity=min((m.severity for m in members), key=lambda s: SEV_RANK[s]),
                rule_ids=[r for r, _ in Counter(m.rule_id for m in members).most_common()],
                top_terms=top_terms([m.description for m in members]),
                top_files=[f for f, _ in Counter(m.file for m in members).most_common(3)],
                sample_ids=[m.id for m in members[:5]],
            )
        )
    return sorted(clusters, key=lambda c: (SEV_RANK[c.highest_severity], -c.size))


def build_insights(db: Session, analysis: Analysis) -> InsightsResponse:
    _require_completed(analysis)
    aid = analysis.id
    rank = case({k: v for k, v in SEV_RANK.items()}, value=Issue.severity, else_=4)

    issues = list(
        db.scalars(
            select(Issue).where(Issue.analysis_id == aid).order_by(rank, Issue.id).limit(MAX_CLUSTERED + 1)
        )
    )
    truncated = len(issues) > MAX_CLUSTERED
    issues = issues[:MAX_CLUSTERED]
    findings = list(
        db.scalars(
            select(SecurityFinding).where(SecurityFinding.analysis_id == aid).limit(MAX_CLUSTERED)
        )
    )

    issue_items = [
        _Item(i.id, i.rule_id, i.title.split(":")[0], i.description, i.severity.value, i.file)
        for i in issues
    ]
    security_items = [
        _Item(f.id, f.rule_id, RULE_NAMES.get(f.rule_id, f.rule_id), f.description, f.severity.value, f.file)
        for f in findings
    ]

    open_conditions = (Issue.analysis_id == aid, Issue.status == IssueStatus.OPEN)
    plan = improvement_plan(
        count_by(db, Issue.severity, *open_conditions),
        count_by(db, SecurityFinding.severity, SecurityFinding.analysis_id == aid),
        count_by(db, Issue.category, *open_conditions),
    )

    return InsightsResponse(
        summary=analysis.ai_summary,
        recommendations=plan,
        issue_clusters=_clusterize(issue_items),
        security_clusters=_clusterize(security_items),
        clustered_issue_count=len(issue_items),
        truncated=truncated,
    )
