import logging
import threading
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session, joinedload

from app.analysis.engine import AnalysisResult, analyze_directory
from app.core.database import SessionLocal
from app.core.errors import AnalysisFailedError, AppError, ConflictError, NotFoundError
from app.core.permissions import Permission
from app.ingestion.git_client import clone_repository
from app.ingestion.github import validate_branch
from app.intelligence.summary import SummaryInput, generate_summary
from app.models import (
    Analysis,
    AnalysisFile,
    AnalysisStatus,
    Issue,
    IssueStatus,
    QualityMetric,
    Repository,
    SecurityFinding,
    Severity,
    User,
)
from app.services import project_service
from app.services.audit_service import log_action
from app.services.project_service import ProjectAccess

logger = logging.getLogger("codescope.analysis")

# At most 2 analyses clone/analyze at the same time; extra ones wait as PENDING.
_slots = threading.BoundedSemaphore(2)

MAX_STORED_FINDINGS = 5000
MAX_WARNINGS = 20


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================ authorization
def get_analysis_access(
    db: Session, analysis_id: int, user: User, permission: Permission
) -> tuple[Analysis, ProjectAccess]:
    analysis = db.scalar(
        select(Analysis)
        .options(joinedload(Analysis.repository), joinedload(Analysis.metrics))
        .where(Analysis.id == analysis_id)
    )
    if analysis is None:
        raise NotFoundError("Analysis not found.")
    try:
        access = project_service.get_project_access(
            db, analysis.repository.project_id, user, permission
        )
    except NotFoundError:
        raise NotFoundError("Analysis not found.") from None
    return analysis, access


# ================================================================== start
def start_analysis(
    db: Session, repo: Repository, user: User, requested_branch: str | None
) -> tuple[Analysis, str | None]:
    """Creates the PENDING row. The heavy work happens later, in the background."""
    branch = (requested_branch or "").strip() or None
    if branch:
        branch = validate_branch(branch)

    active = db.scalar(
        select(Analysis.id)
        .where(
            Analysis.repository_id == repo.id,
            Analysis.status.in_([AnalysisStatus.PENDING, AnalysisStatus.RUNNING]),
        )
        .limit(1)
    )
    if active:
        raise ConflictError("An analysis is already in progress for this repository.")

    analysis = Analysis(
        repository_id=repo.id,
        triggered_by=user.id,
        branch=branch or repo.default_branch,  # for display; the real branch is set after cloning
        status=AnalysisStatus.PENDING,
        progress=0,
    )
    db.add(analysis)
    db.flush()
    log_action(
        db,
        action="analysis_started",
        user_id=user.id,
        project_id=repo.project_id,
        resource_type="analysis",
        resource_id=analysis.id,
        detail=f"{user.name} ran an analysis on {repo.name}",
    )
    db.commit()
    return analysis, branch


# ============================================================ background job
def run_analysis(analysis_id: int, requested_branch: str | None) -> None:
    """Runs in a background thread, with its OWN database sessions."""
    with _slots:
        try:
            _execute(analysis_id, requested_branch)
        except AppError as exc:
            _mark_failed(analysis_id, exc.message)
        except Exception:  # noqa: BLE001
            logger.exception("Analysis %s crashed", analysis_id)
            _mark_failed(analysis_id, "The analysis failed unexpectedly. Please try again.")


def _execute(analysis_id: int, requested_branch: str | None) -> None:
    db = SessionLocal()
    try:
        analysis = db.scalar(
            select(Analysis)
            .options(joinedload(Analysis.repository))
            .where(Analysis.id == analysis_id)
        )
        if analysis is None or analysis.status != AnalysisStatus.PENDING:
            return
        repo = analysis.repository

        analysis.status = AnalysisStatus.RUNNING
        analysis.started_at = _now()
        analysis.progress = 5
        db.commit()

        last_saved = {"progress": 5}

        def on_progress(done: int, total: int) -> None:
            # Map "files done" onto 15..90 and only write to the DB every ~5 points.
            progress = 15 + int(75 * done / max(total, 1))
            if progress - last_saved["progress"] >= 5 or done == total:
                analysis.progress = progress
                db.commit()
                last_saved["progress"] = progress

        with clone_repository(repo.url, requested_branch) as cloned:
            analysis.branch = cloned.branch
            analysis.commit_sha = cloned.commit_sha
            analysis.progress = 15
            db.commit()
            last_saved["progress"] = 15

            result = analyze_directory(cloned.path, on_progress=on_progress)
        # <- the temporary clone has been deleted by this point

        if result.files_analyzed == 0:
            raise AnalysisFailedError(
                "No supported source files (Python, JavaScript, TypeScript) were found."
            )

        _persist_results(db, analysis, repo, result)
    finally:
        db.close()


def _ignored_from_previous(db: Session, analysis: Analysis, repo: Repository) -> dict:
    """(rule_id, file, title) -> (resolved_by, resolved_at) for issues ignored in the last completed analysis."""
    previous_id = db.scalar(
        select(Analysis.id)
        .where(
            Analysis.repository_id == repo.id,
            Analysis.status == AnalysisStatus.COMPLETED,
            Analysis.id != analysis.id,
        )
        .order_by(Analysis.id.desc())
        .limit(1)
    )
    if previous_id is None:
        return {}
    rows = db.execute(
        select(Issue.rule_id, Issue.file, Issue.title, Issue.resolved_by, Issue.resolved_at).where(
            Issue.analysis_id == previous_id, Issue.status == IssueStatus.IGNORED
        )
    ).all()
    return {(r.rule_id, r.file, r.title): (r.resolved_by, r.resolved_at) for r in rows}


def _persist_results(
    db: Session, analysis: Analysis, repo: Repository, result: AnalysisResult
) -> None:
    analysis.progress = 92
    db.commit()

    issues = result.issues[:MAX_STORED_FINDINGS]  # already sorted worst-first
    security = result.security_findings[:MAX_STORED_FINDINGS]

    notes = list(result.warnings)
    if len(result.issues) > MAX_STORED_FINDINGS:
        notes.append(
            f"Only the {MAX_STORED_FINDINGS} most severe of {len(result.issues)} issues were stored."
        )
    if len(result.security_findings) > MAX_STORED_FINDINGS:
        notes.append(
            f"Only the {MAX_STORED_FINDINGS} most severe of "
            f"{len(result.security_findings)} security findings were stored."
        )

    db.add_all(
        AnalysisFile(
            analysis_id=analysis.id,
            path=f.path[:1000],
            language=f.language,
            lines_of_code=f.lines_of_code,
            function_count=f.function_count,
            class_count=f.class_count,
            import_count=f.import_count,
            max_complexity=f.max_complexity,
            avg_complexity=round(f.avg_complexity, 2),
        )
        for f in result.files
    )

    carried = _ignored_from_previous(db, analysis, repo)

    def to_issue(f) -> Issue:
        ignored = carried.get((f.rule_id, f.file[:1000], f.title[:200]))
        return Issue(
            analysis_id=analysis.id,
            rule_id=f.rule_id,
            file=f.file[:1000],
            line=f.line,
            category=f.category,
            severity=Severity(f.severity.value),  # engine enum -> database enum
            title=f.title[:200],
            description=f.description,
            recommendation=f.recommendation,
            status=IssueStatus.IGNORED if ignored else IssueStatus.OPEN,
            resolved_by=ignored[0] if ignored else None,
            resolved_at=ignored[1] if ignored else None,
        )

    db.add_all(to_issue(f) for f in issues)
    db.add_all(
        SecurityFinding(
            analysis_id=analysis.id,
            rule_id=f.rule_id,
            file=f.file[:1000],
            line=f.line,
            severity=Severity(f.severity.value),
            description=f.description,
            recommendation=f.recommendation,
        )
        for f in security
    )

    s = result.score
    db.add(
        QualityMetric(
            analysis_id=analysis.id,
            overall_score=s.overall,
            code_quality_score=s.code_quality,
            maintainability_score=s.maintainability,
            complexity_score=s.complexity,
            security_score=s.security,
            issue_count=len(issues),
            security_finding_count=len(security),
            avg_complexity=s.details["avg_cyclomatic"],
        )
    )

    previous_overall = db.scalar(
        select(QualityMetric.overall_score)
        .join(Analysis, Analysis.id == QualityMetric.analysis_id)
        .where(
            Analysis.repository_id == repo.id,
            Analysis.status == AnalysisStatus.COMPLETED,
            Analysis.id != analysis.id,
        )
        .order_by(Analysis.id.desc())
        .limit(1)
    )
    analysis.ai_summary = generate_summary(
        SummaryInput(
            repo_name=repo.name,
            overall=s.overall,
            code_quality=s.code_quality,
            maintainability=s.maintainability,
            complexity=s.complexity,
            security=s.security,
            files_analyzed=result.files_analyzed,
            lines_analyzed=result.lines_analyzed,
            issue_severity=dict(Counter(f.severity.value for f in issues)),
            security_severity=dict(Counter(f.severity.value for f in security)),
            issue_categories=dict(Counter(f.category for f in issues)),
            top_files=Counter(f.file for f in issues).most_common(3),
            previous_overall=previous_overall,
        )
    )

    analysis.files_analyzed = result.files_analyzed
    analysis.lines_analyzed = result.lines_analyzed
    analysis.function_count = result.function_count
    analysis.class_count = result.class_count
    analysis.skipped_files = result.skipped_files
    trimmed = [n[:300] for n in notes[:MAX_WARNINGS]]
    if len(notes) > MAX_WARNINGS:
        trimmed.append(f"... and {len(notes) - MAX_WARNINGS} more")
    analysis.warnings_text = "\n".join(trimmed) or None

    repo.language = result.primary_language
    analysis.status = AnalysisStatus.COMPLETED
    analysis.progress = 100
    analysis.completed_at = _now()

    log_action(
        db,
        action="analysis_completed",
        user_id=analysis.triggered_by,
        project_id=repo.project_id,
        resource_type="analysis",
        resource_id=analysis.id,
        detail=f"Analysis of {repo.name} completed with a score of {s.overall:.0f}/100",
    )
    db.commit()


def _mark_failed(analysis_id: int, message: str) -> None:
    # Fresh session: the one that failed may be in a broken transaction.
    db = SessionLocal()
    try:
        analysis = db.scalar(
            select(Analysis)
            .options(joinedload(Analysis.repository))
            .where(Analysis.id == analysis_id)
        )
        if analysis is None:
            return
        analysis.status = AnalysisStatus.FAILED
        analysis.error_message = message[:1000]
        analysis.completed_at = _now()
        log_action(
            db,
            action="analysis_failed",
            user_id=analysis.triggered_by,
            project_id=analysis.repository.project_id,
            resource_type="analysis",
            resource_id=analysis.id,
            detail=f"Analysis of {analysis.repository.name} failed: {message[:200]}",
        )
        db.commit()
    finally:
        db.close()


def fail_interrupted_analyses() -> int:
    """
    Called once at startup. Background jobs live in this process, so after a
    restart nothing is still running: PENDING/RUNNING rows are marked FAILED
    instead of showing a progress bar forever. (Assumes a single server process.)
    """
    try:
        with SessionLocal() as db:
            result = db.execute(
                update(Analysis)
                .where(Analysis.status.in_([AnalysisStatus.PENDING, AnalysisStatus.RUNNING]))
                .values(
                    status=AnalysisStatus.FAILED,
                    error_message="Interrupted by a server restart. Please run the analysis again.",
                    completed_at=func.now(),
                )
            )
            db.commit()
            return result.rowcount or 0
    except Exception:  # noqa: BLE001
        logger.warning("Could not clean up interrupted analyses", exc_info=True)
        return 0


# ================================================================== queries
_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def list_issues(
    db: Session,
    analysis_id: int,
    *,
    severity: Severity | None,
    status: IssueStatus | None,
    category: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Issue], int]:
    conditions = [Issue.analysis_id == analysis_id]
    if severity:
        conditions.append(Issue.severity == severity)
    if status:
        conditions.append(Issue.status == status)
    if category:
        conditions.append(Issue.category == category)

    total = db.scalar(select(func.count()).select_from(Issue).where(*conditions)) or 0
    rank = case(_SEVERITY_ORDER, value=Issue.severity, else_=4)
    items = list(
        db.scalars(
            select(Issue)
            .where(*conditions)
            .order_by(rank, Issue.file, Issue.line, Issue.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return items, total


def list_security_findings(
    db: Session, analysis_id: int, *, severity: Severity | None, limit: int, offset: int
) -> tuple[list[SecurityFinding], int]:
    conditions = [SecurityFinding.analysis_id == analysis_id]
    if severity:
        conditions.append(SecurityFinding.severity == severity)

    total = db.scalar(select(func.count()).select_from(SecurityFinding).where(*conditions)) or 0
    rank = case(_SEVERITY_ORDER, value=SecurityFinding.severity, else_=4)
    items = list(
        db.scalars(
            select(SecurityFinding)
            .where(*conditions)
            .order_by(rank, SecurityFinding.file, SecurityFinding.line, SecurityFinding.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return items, total
