from enum import Enum

from app.models import Role


class Permission(str, Enum):
    VIEW_REPORTS = "view_reports"
    RUN_ANALYSIS = "run_analysis"
    EDIT_PROJECT = "edit_project"
    MANAGE_MEMBERS = "manage_members"   # invite / remove members
    CHANGE_ROLES = "change_roles"
    DELETE_PROJECT = "delete_project"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({Permission.VIEW_REPORTS}),
    Role.MEMBER: frozenset({Permission.VIEW_REPORTS, Permission.RUN_ANALYSIS}),
    Role.ADMIN: frozenset(
        {
            Permission.VIEW_REPORTS,
            Permission.RUN_ANALYSIS,
            Permission.EDIT_PROJECT,
            Permission.MANAGE_MEMBERS,
        }
    ),
    Role.OWNER: frozenset(Permission),  # every permission
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
