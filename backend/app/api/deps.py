from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import UnauthorizedError
from app.core.permissions import Permission
from app.core.security import decode_access_token
from app.models import User
from app.services import project_service
from app.services.project_service import ProjectAccess

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Authentication required.")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise UnauthorizedError("Invalid or expired access token.")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or disabled.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_project_permission(permission: Permission):
    """
    Dependency factory. Usage in a route:

        access: Annotated[ProjectAccess, Depends(require_project_permission(Permission.EDIT_PROJECT))]

    It reads `project_id` from the URL path, checks membership AND permission,
    and hands the route a verified ProjectAccess object.
    """

    def dependency(project_id: int, db: DbSession, user: CurrentUser) -> ProjectAccess:
        return project_service.get_project_access(db, project_id, user, permission)

    return dependency


# Ready-made aliases so routes stay short and readable
CanView = Annotated[ProjectAccess, Depends(require_project_permission(Permission.VIEW_REPORTS))]
CanRun = Annotated[ProjectAccess, Depends(require_project_permission(Permission.RUN_ANALYSIS))]
CanEdit = Annotated[ProjectAccess, Depends(require_project_permission(Permission.EDIT_PROJECT))]
CanManageMembers = Annotated[
    ProjectAccess, Depends(require_project_permission(Permission.MANAGE_MEMBERS))
]
CanChangeRoles = Annotated[
    ProjectAccess, Depends(require_project_permission(Permission.CHANGE_ROLES))
]
CanDelete = Annotated[ProjectAccess, Depends(require_project_permission(Permission.DELETE_PROJECT))]
