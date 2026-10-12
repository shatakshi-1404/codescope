import pytest

from app.core.permissions import ROLE_PERMISSIONS, Permission, has_permission
from app.models import Role

ALL = set(Permission)
EXPECTED = {
    Role.OWNER: ALL,
    Role.ADMIN: {Permission.VIEW_REPORTS, Permission.RUN_ANALYSIS, Permission.EDIT_PROJECT, Permission.MANAGE_MEMBERS},
    Role.MEMBER: {Permission.VIEW_REPORTS, Permission.RUN_ANALYSIS},
    Role.VIEWER: {Permission.VIEW_REPORTS},
}


@pytest.mark.parametrize("role", list(Role))
def test_matrix_matches_the_spec(role):
    assert set(ROLE_PERMISSIONS[role]) == EXPECTED[role]


def test_roles_are_strictly_nested():
    p = ROLE_PERMISSIONS
    assert p[Role.VIEWER] < p[Role.MEMBER] < p[Role.ADMIN] < p[Role.OWNER]


def test_only_the_owner_can_delete_or_change_roles():
    for role in (Role.ADMIN, Role.MEMBER, Role.VIEWER):
        assert not has_permission(role, Permission.DELETE_PROJECT)
        assert not has_permission(role, Permission.CHANGE_ROLES)
    assert has_permission(Role.OWNER, Permission.DELETE_PROJECT)
    assert has_permission(Role.OWNER, Permission.CHANGE_ROLES)


def test_viewers_can_only_view():
    assert has_permission(Role.VIEWER, Permission.VIEW_REPORTS)
    assert not has_permission(Role.VIEWER, Permission.RUN_ANALYSIS)
