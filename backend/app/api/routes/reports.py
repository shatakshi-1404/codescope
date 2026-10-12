from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.permissions import Permission
from app.schemas.report import FilePage, HistoryPoint, InsightsResponse, ReportResponse
from app.services import analysis_service, report_service, repository_service

router = APIRouter(tags=["reports"])


@router.get("/analyses/{analysis_id}/report", response_model=ReportResponse)
def get_report(analysis_id: int, db: DbSession, user: CurrentUser):
    analysis, _ = analysis_service.get_analysis_access(db, analysis_id, user, Permission.VIEW_REPORTS)
    return report_service.build_report(db, analysis)


@router.get("/analyses/{analysis_id}/insights", response_model=InsightsResponse)
def get_insights(analysis_id: int, db: DbSession, user: CurrentUser):
    analysis, _ = analysis_service.get_analysis_access(db, analysis_id, user, Permission.VIEW_REPORTS)
    return report_service.build_insights(db, analysis)


@router.get("/analyses/{analysis_id}/files", response_model=FilePage)
def list_files(
    analysis_id: int,
    db: DbSession,
    user: CurrentUser,
    sort: Literal["path", "lines", "complexity", "functions"] = "complexity",
    descending: bool = True,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    analysis, _ = analysis_service.get_analysis_access(db, analysis_id, user, Permission.VIEW_REPORTS)
    return report_service.list_files(
        db, analysis, sort=sort, descending=descending, limit=limit, offset=offset
    )


@router.get("/repositories/{repository_id}/history", response_model=list[HistoryPoint])
def repository_history(
    repository_id: int,
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
):
    repo, _ = repository_service.get_repository_access(db, repository_id, user, Permission.VIEW_REPORTS)
    return report_service.repository_history(db, repo.id, limit)
