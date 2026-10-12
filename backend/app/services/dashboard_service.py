from collections import defaultdict
from statistics import fmean

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Analysis,
    AnalysisStatus,
    AuditLog,
    Issue,
    IssueStatus,
    ProjectMember,
    QualityMetric,
    Repository,
    SecurityFinding,
    Severity,
    User,
)
from app.schemas.analysis import IssueResponse
from app.schemas.dashboard import (
    ActivityPage,
    ActivityResponse,
    DashboardResponse,
    DashboardStats,
    ProjectIssuePage,
    ProjectIssueResponse,
    RecentAnalysis,
    RecentAnalysisPage,
    TrendPoint,
)
from app.services.analysis_service import _SEVERITY_ORDER as SEVERITY_ORDER
from app.services.report_service import SEV_KEYS, count_by, full_counts


def _user_repo_ids(user: User):
    projects = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    return select(Repository.id).where(Repository.project_id.in_(projects))


def _latest_completed_ids(db: Session, repo_ids) -> list[int]:
    """Newest completed analysis per repository. Counting every historical analysis would double-count issues."""
    return list(
        db.scalars(
            select(func.max(Analysis.id))
            .where(Analysis.repository_id.in_(repo_ids), Analysis.status == AnalysisStatus.COMPLETED)
            .group_by(Analysis.repository_id)
        )
    )


def _recent_item(a: Analysis) -> RecentAnalysis:
    return RecentAnalysis(
        id=a.id,
        project_id=a.repository.project_id,
        repository_id=a.repository_id,
        repository_name=a.repository.name,
        branch=a.branch,
        status=a.status,
        progress=a.progress,
        quality=a.metrics.overall_score if a.metrics else None,
        issue_count=a.metrics.issue_count if a.metrics else 0,
        created_at=a.created_at,
    )


def _recent_query(repo_ids):
    return (
        select(Analysis)
        .options(joinedload(Analysis.repository), joinedload(Analysis.metrics))
        .where(Analysis.repository_id.in_(repo_ids))
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
    )


# ================================================================ dashboard
def get_dashboard(db: Session, user: User) -> DashboardResponse:
    repo_ids = _user_repo_ids(user)
    latest = _latest_completed_ids(db, repo_ids)

    projects = db.scalar(
        select(func.count()).select_from(ProjectMember).where(ProjectMember.user_id == user.id)
    ) or 0
    repositories = db.scalar(select(func.count()).select_from(Repository).where(Repository.id.in_(repo_ids))) or 0

    issue_distribution = dict.fromkeys(SEV_KEYS, 0)
    security_distribution = dict.fromkeys(SEV_KEYS, 0)
    average_quality = None
    if latest:
        issue_distribution = full_counts(
            count_by(db, Issue.severity, Issue.analysis_id.in_(latest), Issue.status == IssueStatus.OPEN),
            SEV_KEYS,
        )
        security_distribution = full_counts(
            count_by(db, SecurityFinding.severity, SecurityFinding.analysis_id.in_(latest)), SEV_KEYS
        )
        avg = db.scalar(select(func.avg(QualityMetric.overall_score)).where(QualityMetric.analysis_id.in_(latest)))
        average_quality = round(avg, 1) if avg is not None else None

    # ---- trend: one point per calendar day (averages), newest 60 analyses
    rows = db.execute(
        select(
            Analysis.completed_at,
            QualityMetric.overall_score,
            QualityMetric.avg_complexity,
            QualityMetric.issue_count,
            QualityMetric.security_finding_count,
        )
        .join(QualityMetric, QualityMetric.analysis_id == Analysis.id)
        .where(
            Analysis.repository_id.in_(repo_ids),
            Analysis.status == AnalysisStatus.COMPLETED,
            Analysis.completed_at.is_not(None),
        )
        .order_by(Analysis.id.desc())
        .limit(60)
    ).all()
    by_day: dict[str, list[tuple]] = defaultdict(list)
    for completed_at, overall, complexity, issues, security in reversed(rows):
        by_day[completed_at.date().isoformat()].append((overall, complexity, issues, security))
    trend = [
        TrendPoint(
            date=day,
            quality=round(fmean(p[0] for p in points), 1),
            complexity=round(fmean(p[1] for p in points), 2),
            issues=round(fmean(p[2] for p in points)),
            security_findings=round(fmean(p[3] for p in points)),
        )
        for day, points in by_day.items()
    ]

    recent = list(db.scalars(_recent_query(repo_ids).limit(10)).unique())

    return DashboardResponse(
        stats=DashboardStats(
            projects=projects,
            repositories=repositories,
            repositories_analyzed=len(latest),
            open_issues=sum(issue_distribution.values()),
            average_quality=average_quality,
        ),
        issue_distribution=issue_distribution,
        security_distribution=security_distribution,
        trend=trend,
        recent_analyses=[_recent_item(a) for a in recent],
    )


# ============================================================ project views
def list_project_analyses(db: Session, project_id: int, limit: int, offset: int) -> RecentAnalysisPage:
    repo_ids = select(Repository.id).where(Repository.project_id == project_id)
    total = db.scalar(select(func.count()).select_from(Analysis).where(Analysis.repository_id.in_(repo_ids))) or 0
    rows = list(db.scalars(_recent_query(repo_ids).limit(limit).offset(offset)).unique())
    return RecentAnalysisPage(items=[_recent_item(a) for a in rows], total=total, limit=limit, offset=offset)


def list_project_issues(
    db: Session,
    project_id: int,
    *,
    severity: Severity | None,
    status: IssueStatus | None,
    category: str | None,
    repository_id: int | None,
    limit: int,
    offset: int,
) -> ProjectIssuePage:
    """Issues from the NEWEST completed analysis of each repository in the project."""
    latest = _latest_completed_ids(db, select(Repository.id).where(Repository.project_id == project_id))
    if not latest:
        return ProjectIssuePage(items=[], total=0, limit=limit, offset=offset)

    conditions = [Issue.analysis_id.in_(latest)]
    if severity:
        conditions.append(Issue.severity == severity)
    if status:
        conditions.append(Issue.status == status)
    if category:
        conditions.append(Issue.category == category)
    if repository_id:
        conditions.append(Analysis.repository_id == repository_id)

    joins = lambda stmt: stmt.join(Analysis, Analysis.id == Issue.analysis_id).join(  # noqa: E731
        Repository, Repository.id == Analysis.repository_id
    )
    total = db.scalar(joins(select(func.count()).select_from(Issue)).where(*conditions)) or 0
    rank = case(SEVERITY_ORDER, value=Issue.severity, else_=4)
    rows = db.execute(
        joins(select(Issue, Repository.name))
        .where(*conditions)
        .order_by(rank, Issue.file, Issue.line, Issue.id)
        .limit(limit)
        .offset(offset)
    ).all()

    return ProjectIssuePage(
        items=[
            ProjectIssueResponse(**IssueResponse.model_validate(i).model_dump(), repository_name=name)
            for i, name in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# ================================================================= activity
def _activity_page(db: Session, condition, limit: int, offset: int) -> ActivityPage:
    total = db.scalar(select(func.count()).select_from(AuditLog).where(condition)) or 0
    rows = db.scalars(
        select(AuditLog)
        .options(joinedload(AuditLog.user))
        .where(condition)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return ActivityPage(
        items=[
            ActivityResponse(
                id=r.id,
                project_id=r.project_id,
                user_id=r.user_id,
                user_name=r.user.name if r.user else "Unknown user",
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                detail=r.detail or r.action.replace("_", " "),
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


def project_activity(db: Session, project_id: int, limit: int, offset: int) -> ActivityPage:
    return _activity_page(db, AuditLog.project_id == project_id, limit, offset)


def user_activity(db: Session, user: User, limit: int, offset: int) -> ActivityPage:
    mine = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    return _activity_page(db, AuditLog.project_id.in_(mine), limit, offset)
