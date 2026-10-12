from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Analysis, AnalysisStatus, IssueStatus, Severity


class AnalyzeRequest(BaseModel):
    branch: str | None = Field(default=None, max_length=200)


class ScoresResponse(BaseModel):
    overall: float
    code_quality: float
    maintainability: float
    complexity: float
    security: float


class AnalysisResponse(BaseModel):
    id: int
    repository_id: int
    project_id: int
    repository_name: str
    branch: str | None
    commit_sha: str | None
    status: AnalysisStatus
    progress: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    files_analyzed: int
    lines_analyzed: int
    function_count: int
    class_count: int
    issue_count: int
    security_finding_count: int
    skipped_files: int
    warnings: list[str]
    scores: ScoresResponse | None
    ai_summary: str | None

    @classmethod
    def from_model(cls, a: Analysis) -> "AnalysisResponse":
        m = a.metrics
        return cls(
            id=a.id,
            repository_id=a.repository_id,
            project_id=a.repository.project_id,
            repository_name=a.repository.name,
            branch=a.branch,
            commit_sha=a.commit_sha,
            status=a.status,
            progress=a.progress,
            error_message=a.error_message,
            created_at=a.created_at,
            started_at=a.started_at,
            completed_at=a.completed_at,
            files_analyzed=a.files_analyzed,
            lines_analyzed=a.lines_analyzed,
            function_count=a.function_count,
            class_count=a.class_count,
            issue_count=m.issue_count if m else 0,
            security_finding_count=m.security_finding_count if m else 0,
            skipped_files=a.skipped_files or 0,
            warnings=a.warnings_text.split("\n") if a.warnings_text else [],
            scores=(
                ScoresResponse(
                    overall=m.overall_score,
                    code_quality=m.code_quality_score,
                    maintainability=m.maintainability_score,
                    complexity=m.complexity_score,
                    security=m.security_score,
                )
                if m
                else None
            ),
            ai_summary=a.ai_summary,
        )


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_id: int
    rule_id: str
    file: str
    line: int
    category: str
    severity: Severity
    title: str
    description: str
    recommendation: str
    status: IssueStatus
    resolved_by: int | None
    resolved_at: datetime | None


class IssuePage(BaseModel):
    items: list[IssueResponse]
    total: int
    limit: int
    offset: int


class SecurityFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_id: int
    rule_id: str
    file: str
    line: int
    severity: Severity
    description: str
    recommendation: str


class SecurityFindingPage(BaseModel):
    label: str = "Static Security Checks"
    items: list[SecurityFindingResponse]
    total: int
    limit: int
    offset: int
