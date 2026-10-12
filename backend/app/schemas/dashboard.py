from datetime import datetime

from pydantic import BaseModel

from app.models import AnalysisStatus
from app.schemas.analysis import IssueResponse


class DashboardStats(BaseModel):
    projects: int
    repositories: int
    repositories_analyzed: int
    open_issues: int
    average_quality: float | None


class TrendPoint(BaseModel):
    date: str
    quality: float
    complexity: float
    issues: int
    security_findings: int


class RecentAnalysis(BaseModel):
    id: int
    project_id: int
    repository_id: int
    repository_name: str
    branch: str | None
    status: AnalysisStatus
    progress: int
    quality: float | None
    issue_count: int
    created_at: datetime


class DashboardResponse(BaseModel):
    stats: DashboardStats
    issue_distribution: dict[str, int]       # open issues by severity (latest analysis per repo)
    security_distribution: dict[str, int]    # static security findings by severity
    trend: list[TrendPoint]
    recent_analyses: list[RecentAnalysis]


class RecentAnalysisPage(BaseModel):
    items: list[RecentAnalysis]
    total: int
    limit: int
    offset: int


class ProjectIssueResponse(IssueResponse):
    repository_name: str


class ProjectIssuePage(BaseModel):
    items: list[ProjectIssueResponse]
    total: int
    limit: int
    offset: int


class ActivityResponse(BaseModel):
    id: int
    project_id: int | None
    user_id: int | None
    user_name: str
    action: str
    resource_type: str | None
    resource_id: int | None
    detail: str
    created_at: datetime


class ActivityPage(BaseModel):
    items: list[ActivityResponse]
    total: int
    limit: int
    offset: int
