from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.permissions import Permission
from app.models import Analysis, Issue, IssueStatus, Repository, User
from app.services import project_service
from app.services.audit_service import log_action
from app.services.project_service import ProjectAccess

_ACTIONS = {
    IssueStatus.RESOLVED: ("issue_resolved", "resolved"),
    IssueStatus.IGNORED: ("issue_ignored", "ignored"),
    IssueStatus.OPEN: ("issue_reopened", "reopened"),
}


def get_issue_access(
    db: Session, issue_id: int, user: User, permission: Permission
) -> tuple[Issue, ProjectAccess]:
    """issue -> analysis -> repository -> project, then the normal membership check."""
    row = db.execute(
        select(Issue, Repository.project_id)
        .join(Analysis, Analysis.id == Issue.analysis_id)
        .join(Repository, Repository.id == Analysis.repository_id)
        .where(Issue.id == issue_id)
    ).first()
    if row is None:
        raise NotFoundError("Issue not found.")
    issue, project_id = row
    try:
        access = project_service.get_project_access(db, project_id, user, permission)
    except NotFoundError:
        raise NotFoundError("Issue not found.") from None
    return issue, access


def change_status(
    db: Session, issue: Issue, access: ProjectAccess, new_status: IssueStatus
) -> Issue:
    if issue.status == new_status:
        return issue  # idempotent: no duplicate audit rows

    issue.status = new_status
    if new_status == IssueStatus.OPEN:
        issue.resolved_by = None
        issue.resolved_at = None
    else:
        issue.resolved_by = access.user.id
        issue.resolved_at = datetime.now(timezone.utc)

    action, verb = _ACTIONS[new_status]
    log_action(
        db,
        action=action,
        user_id=access.user.id,
        project_id=access.project.id,
        resource_type="issue",
        resource_id=issue.id,
        detail=f'{access.user.name} {verb} "{issue.title}" ({issue.file}:{issue.line})'[:500],
    )
    db.commit()
    return issue
