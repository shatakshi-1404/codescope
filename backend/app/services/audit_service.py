from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(
    db: Session,
    *,
    action: str,
    user_id: int | None,
    project_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    detail: str | None = None,
) -> None:
    """Adds an audit row. The caller is responsible for commit()."""
    db.add(
        AuditLog(
            action=action,
            user_id=user_id,
            project_id=project_id,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
        )
    )
