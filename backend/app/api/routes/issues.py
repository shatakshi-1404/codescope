from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.permissions import Permission
from app.schemas.analysis import IssueResponse
from app.schemas.issue import IssueStatusUpdate
from app.services import issue_service

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(issue_id: int, db: DbSession, user: CurrentUser):
    issue, _ = issue_service.get_issue_access(db, issue_id, user, Permission.VIEW_REPORTS)
    return IssueResponse.model_validate(issue)


@router.patch("/{issue_id}/status", response_model=IssueResponse)
def update_issue_status(issue_id: int, body: IssueStatusUpdate, db: DbSession, user: CurrentUser):
    # MEMBER and above can triage issues; VIEWERs get 403.
    issue, access = issue_service.get_issue_access(db, issue_id, user, Permission.RUN_ANALYSIS)
    issue = issue_service.change_status(db, issue, access, body.status)
    return IssueResponse.model_validate(issue)
