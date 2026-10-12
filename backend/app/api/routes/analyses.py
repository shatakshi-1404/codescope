from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.permissions import Permission
from app.models import IssueStatus, Severity
from app.schemas.analysis import (
    AnalysisResponse,
    IssuePage,
    IssueResponse,
    SecurityFindingPage,
    SecurityFindingResponse,
)
from app.services import analysis_service

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, db: DbSession, user: CurrentUser):
    """Also used for polling: check `status` and `progress` until COMPLETED / FAILED."""
    analysis, _ = analysis_service.get_analysis_access(
        db, analysis_id, user, Permission.VIEW_REPORTS
    )
    return AnalysisResponse.from_model(analysis)


@router.get("/{analysis_id}/issues", response_model=IssuePage)
def list_issues(
    analysis_id: int,
    db: DbSession,
    user: CurrentUser,
    severity: Severity | None = None,
    status_filter: IssueStatus | None = Query(default=None, alias="status"),
    category: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    analysis_service.get_analysis_access(db, analysis_id, user, Permission.VIEW_REPORTS)
    items, total = analysis_service.list_issues(
        db,
        analysis_id,
        severity=severity,
        status=status_filter,
        category=category,
        limit=limit,
        offset=offset,
    )
    return IssuePage(
        items=[IssueResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{analysis_id}/security", response_model=SecurityFindingPage)
def list_security_findings(
    analysis_id: int,
    db: DbSession,
    user: CurrentUser,
    severity: Severity | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    analysis_service.get_analysis_access(db, analysis_id, user, Permission.VIEW_REPORTS)
    items, total = analysis_service.list_security_findings(
        db, analysis_id, severity=severity, limit=limit, offset=offset
    )
    return SecurityFindingPage(
        items=[SecurityFindingResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )
