from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.dashboard import ActivityPage, DashboardResponse
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: DbSession, user: CurrentUser):
    return dashboard_service.get_dashboard(db, user)


@router.get("/activity", response_model=ActivityPage)
def my_activity(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Activity across every project the user belongs to."""
    return dashboard_service.user_activity(db, user, limit, offset)
