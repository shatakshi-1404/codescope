from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.permissions import Permission, has_permission
from app.models import Project, ProjectMember, Role, User
from app.services.audit_service import log_action


@dataclass
class ProjectAccess:
    """Result of a successful authorization check."""

    project: Project
    membership: ProjectMember
    user: User

    @property
    def role(self) -> Role:
        return self.membership.role


# ---------------------------------------------------------------- authorization
def get_project_access(
    db: Session, project_id: int, user: User, permission: Permission
) -> ProjectAccess:
    """
    Object-level authorization.

    1. Not a member -> 404 (we don't reveal that the project exists).
    2. Member without the permission -> 403.
    The lookup is done by (project_id AND user_id), so changing the ID in the
    URL can never expose someone else's project.
    """
    row = db.execute(
        select(Project, ProjectMember)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(Project.id == project_id, ProjectMember.user_id == user.id)
    ).first()

    if row is None:
        raise NotFoundError("Project not found.")

    project, membership = row
    if not has_permission(membership.role, permission):
        raise ForbiddenError("You don't have permission to do this in this project.")

    return ProjectAccess(project=project, membership=membership, user=user)


# --------------------------------------------------------------------- projects
def create_project(
    db: Session, *, user: User, name: str, description: str | None
) -> tuple[Project, Role]:
    project = Project(owner_id=user.id, name=name, description=description)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role=Role.OWNER))
    log_action(
        db,
        action="project_created",
        user_id=user.id,
        project_id=project.id,
        resource_type="project",
        resource_id=project.id,
        detail=f"{user.name} created project {project.name}",
    )
    db.commit()
    return project, Role.OWNER


def list_projects(db: Session, user: User) -> list[tuple[Project, Role]]:
    rows = db.execute(
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.created_at.desc())
    ).all()
    return [(p, r) for p, r in rows]


def update_project(db: Session, access: ProjectAccess, changes: dict) -> Project:
    project = access.project
    for field in ("name", "description"):
        if field in changes:
            setattr(project, field, changes[field])
    if changes:
        log_action(
            db,
            action="project_updated",
            user_id=access.user.id,
            project_id=project.id,
            resource_type="project",
            resource_id=project.id,
            detail=f"{access.user.name} updated project {project.name}",
        )
    db.commit()
    return project


def delete_project(db: Session, access: ProjectAccess) -> None:
    project = access.project
    # Logged without project_id: audit rows tied to the project are deleted with it.
    log_action(
        db,
        action="project_deleted",
        user_id=access.user.id,
        resource_type="project",
        resource_id=project.id,
        detail=f"{access.user.name} deleted project {project.name}",
    )
    db.delete(project)
    db.commit()


# ---------------------------------------------------------------------- members
def list_members(db: Session, project_id: int) -> list[ProjectMember]:
    return list(
        db.scalars(
            select(ProjectMember)
            .options(joinedload(ProjectMember.user))
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at)
        )
    )


def _get_member_in_project(db: Session, project_id: int, member_id: int) -> ProjectMember:
    """
    Child-resource check: the member row must belong to THIS project.
    Without this, someone could pass their own project ID with another
    project's member ID.
    """
    member = db.scalar(
        select(ProjectMember)
        .options(joinedload(ProjectMember.user))
        .where(ProjectMember.id == member_id, ProjectMember.project_id == project_id)
    )
    if member is None:
        raise NotFoundError("Member not found.")
    return member


def invite_member(
    db: Session, access: ProjectAccess, *, email: str, role: Role
) -> ProjectMember:
    if role == Role.OWNER:
        raise BusinessRuleError("A project has exactly one owner; OWNER cannot be assigned.")
    if role == Role.ADMIN and access.role != Role.OWNER:
        raise ForbiddenError("Only the project owner can add admins.")

    invitee = db.scalar(select(User).where(User.email == email.lower()))
    if invitee is None:
        raise NotFoundError("No CodeScope user with that email. Ask them to register first.")

    existing = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == access.project.id,
            ProjectMember.user_id == invitee.id,
        )
    )
    if existing:
        raise ConflictError("That user is already a member of this project.")

    member = ProjectMember(project_id=access.project.id, user_id=invitee.id, role=role)
    db.add(member)
    db.flush()
    log_action(
        db,
        action="member_invited",
        user_id=access.user.id,
        project_id=access.project.id,
        resource_type="member",
        resource_id=member.id,
        detail=f"{invitee.name} was added as {role.value}",
    )
    db.commit()
    member.user = invitee
    return member


def change_member_role(
    db: Session, access: ProjectAccess, *, member_id: int, new_role: Role
) -> ProjectMember:
    member = _get_member_in_project(db, access.project.id, member_id)

    if member.role == Role.OWNER:
        raise BusinessRuleError("The owner's role cannot be changed.")
    if new_role == Role.OWNER:
        raise BusinessRuleError("OWNER cannot be assigned.")

    old_role = member.role
    member.role = new_role
    log_action(
        db,
        action="member_role_changed",
        user_id=access.user.id,
        project_id=access.project.id,
        resource_type="member",
        resource_id=member.id,
        detail=f"{member.user.name} changed from {old_role.value} to {new_role.value}",
    )
    db.commit()
    return member


def remove_member(db: Session, access: ProjectAccess, *, member_id: int) -> None:
    member = _get_member_in_project(db, access.project.id, member_id)

    if member.role == Role.OWNER:
        raise BusinessRuleError("The project owner cannot be removed.")
    # Admins may only remove MEMBER / VIEWER, never other admins.
    if access.role == Role.ADMIN and member.role == Role.ADMIN:
        raise ForbiddenError("Only the project owner can remove admins.")

    log_action(
        db,
        action="member_removed",
        user_id=access.user.id,
        project_id=access.project.id,
        resource_type="member",
        resource_id=member.id,
        detail=f"{member.user.name} was removed from the project",
    )
    db.delete(member)
    db.commit()
