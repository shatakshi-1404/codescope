from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Analysis, AnalysisStatus, Repository


class RepositoryCreate(BaseModel):
    url: str = Field(min_length=1, max_length=300)


class LatestAnalysis(BaseModel):
    id: int
    status: AnalysisStatus
    progress: int
    overall_score: float | None
    created_at: datetime


class RepositoryResponse(BaseModel):
    id: int
    project_id: int
    url: str
    name: str
    default_branch: str | None
    language: str | None
    created_at: datetime
    latest_analysis: LatestAnalysis | None = None

    @classmethod
    def from_model(cls, repo: Repository, latest: Analysis | None) -> "RepositoryResponse":
        return cls(
            id=repo.id,
            project_id=repo.project_id,
            url=repo.url,
            name=repo.name,
            default_branch=repo.default_branch,
            language=repo.language,
            created_at=repo.created_at,
            latest_analysis=(
                LatestAnalysis(
                    id=latest.id,
                    status=latest.status,
                    progress=latest.progress,
                    overall_score=latest.metrics.overall_score if latest.metrics else None,
                    created_at=latest.created_at,
                )
                if latest
                else None
            ),
        )
