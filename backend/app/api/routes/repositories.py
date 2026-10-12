from fastapi import APIRouter, BackgroundTasks, status

from app.api.deps import CanEdit, CanView, CurrentUser, DbSession
from app.core.permissions import Permission
from app.schemas.analysis import AnalysisResponse, AnalyzeRequest
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.services import analysis_service, repository_service

router = APIRouter(tags=["repositories"])


@router.post(
    "/projects/{project_id}/repositories",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_repository(body: RepositoryCreate, access: CanEdit, db: DbSession):
    # Adding repositories needs EDIT_PROJECT (OWNER / ADMIN).
    repo = repository_service.add_repository(db, access, body.url)
    return RepositoryResponse.from_model(repo, None)


@router.get("/projects/{project_id}/repositories", response_model=list[RepositoryResponse])
def list_repositories(access: CanView, db: DbSession):
    rows = repository_service.list_repositories(db, access.project.id)
    return [RepositoryResponse.from_model(repo, latest) for repo, latest in rows]


@router.post(
    "/repositories/{repository_id}/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_repository(
    repository_id: int,
    background: BackgroundTasks,
    db: DbSession,
    user: CurrentUser,
    body: AnalyzeRequest | None = None,
):
    repo, _access = repository_service.get_repository_access(
        db, repository_id, user, Permission.RUN_ANALYSIS
    )
    analysis, clone_branch = analysis_service.start_analysis(
        db, repo, user, body.branch if body else None
    )
    # Respond immediately (202); the clone + analysis runs after the response is sent.
    background.add_task(analysis_service.run_analysis, analysis.id, clone_branch)
    return AnalysisResponse.from_model(analysis)
