from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ConflictError, NotFoundError
from app.core.permissions import Permission
from app.ingestion.git_client import fetch_default_branch
from app.ingestion.github import parse_github_url
from app.models import Analysis, Repository, User
from app.services import project_service
from app.services.audit_service import log_action
from app.services.project_service import ProjectAccess


def get_repository_access(
    db: Session, repository_id: int, user: User, permission: Permission
) -> tuple[Repository, ProjectAccess]:
    """
    Object-level authorization for /repositories/{id}.
    A missing repository and a repository in someone else's project give the
    SAME 404, so IDs cannot be probed.
    """
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise NotFoundError("Repository not found.")
    try:
        access = project_service.get_project_access(db, repo.project_id, user, permission)
    except NotFoundError:
        raise NotFoundError("Repository not found.") from None
    return repo, access


def add_repository(db: Session, access: ProjectAccess, raw_url: str) -> Repository:
    ref = parse_github_url(raw_url)  # validates + normalizes

    duplicate = db.scalar(
        select(Repository.id).where(
            Repository.project_id == access.project.id,
            Repository.url == ref.normalized_url,
        )
    )
    if duplicate:
        raise ConflictError("This repository is already in the project.")

    # Verifies the repo exists and is public, without downloading any code.
    default_branch = fetch_default_branch(ref.normalized_url)

    repo = Repository(
        project_id=access.project.id,
        url=ref.normalized_url,
        name=ref.full_name,
        default_branch=default_branch,
    )
    db.add(repo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("This repository is already in the project.") from None

    log_action(
        db,
        action="repository_added",
        user_id=access.user.id,
        project_id=access.project.id,
        resource_type="repository",
        resource_id=repo.id,
        detail=f"{access.user.name} added repository {ref.full_name}",
    )
    db.commit()
    return repo


def list_repositories(db: Session, project_id: int) -> list[tuple[Repository, Analysis | None]]:
    repos = list(
        db.scalars(
            select(Repository)
            .where(Repository.project_id == project_id)
            .order_by(Repository.created_at.desc())
        )
    )
    result = []
    for repo in repos:
        latest = db.scalar(
            select(Analysis)
            .options(joinedload(Analysis.metrics))
            .where(Analysis.repository_id == repo.id)
            .order_by(Analysis.created_at.desc(), Analysis.id.desc())
            .limit(1)
        )
        result.append((repo, latest))
    return result
