from fastapi import APIRouter, Query

from app.api.deps import CanView, DbSession
from app.models import IssueStatus, Severity
from app.schemas.dashboard import ActivityPage, ProjectIssuePage, RecentAnalysisPage
from app.services import dashboard_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{project_id}/analyses", response_model=RecentAnalysisPage)
def project_analyses(
    access: CanView,
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return dashboard_service.list_project_analyses(db, access.project.id, limit, offset)


@router.get("/{project_id}/issues", response_model=ProjectIssuePage)
def project_issues(
    access: CanView,
    db: DbSession,
    severity: Severity | None = None,
    status: IssueStatus | None = None,
    category: str | None = None,
    repository_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return dashboard_service.list_project_issues(
        db,
        access.project.id,
        severity=severity,
        status=status,
        category=category,
        repository_id=repository_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{project_id}/activity", response_model=ActivityPage)
def project_activity(
    access: CanView,
    db: DbSession,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return dashboard_service.project_activity(db, access.project.id, limit, offset)
