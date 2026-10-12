from fastapi import APIRouter, status

from app.api.deps import (
    CanChangeRoles,
    CanDelete,
    CanEdit,
    CanManageMembers,
    CanView,
    CurrentUser,
    DbSession,
)
from app.models import Project, ProjectMember, Role
from app.schemas.project import (
    MemberInvite,
    MemberResponse,
    MemberRoleUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_out(project: Project, role: Role) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        my_role=role,
    )


def _member_out(m: ProjectMember) -> MemberResponse:
    return MemberResponse(
        id=m.id,
        user_id=m.user_id,
        name=m.user.name,
        email=m.user.email,
        role=m.role,
        created_at=m.created_at,
    )


# ---------------------------------------------------------------- projects
@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: DbSession, user: CurrentUser):
    project, role = project_service.create_project(
        db, user=user, name=body.name, description=body.description
    )
    return _project_out(project, role)


@router.get("", response_model=list[ProjectResponse])
def list_projects(db: DbSession, user: CurrentUser):
    return [_project_out(p, r) for p, r in project_service.list_projects(db, user)]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(access: CanView):
    return _project_out(access.project, access.role)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(body: ProjectUpdate, access: CanEdit, db: DbSession):
    project = project_service.update_project(
        db, access, body.model_dump(exclude_unset=True)
    )
    return _project_out(project, access.role)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(access: CanDelete, db: DbSession):
    project_service.delete_project(db, access)


# ----------------------------------------------------------------- members
@router.get("/{project_id}/members", response_model=list[MemberResponse])
def list_members(access: CanView, db: DbSession):
    return [_member_out(m) for m in project_service.list_members(db, access.project.id)]


@router.post(
    "/{project_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(body: MemberInvite, access: CanManageMembers, db: DbSession):
    member = project_service.invite_member(db, access, email=body.email, role=body.role)
    return _member_out(member)


@router.patch("/{project_id}/members/{member_id}", response_model=MemberResponse)
def change_member_role(
    member_id: int, body: MemberRoleUpdate, access: CanChangeRoles, db: DbSession
):
    member = project_service.change_member_role(
        db, access, member_id=member_id, new_role=body.role
    )
    return _member_out(member)


@router.delete(
    "/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_member(member_id: int, access: CanManageMembers, db: DbSession):
    project_service.remove_member(db, access, member_id=member_id)
