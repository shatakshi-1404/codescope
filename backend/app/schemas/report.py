from datetime import datetime

from pydantic import BaseModel

from app.schemas.analysis import AnalysisResponse, ScoresResponse


# ------------------------------------------------------------------ report
class RuleCount(BaseModel):
    rule_id: str
    name: str
    count: int


class OverviewCards(BaseModel):
    files_analyzed: int
    lines_analyzed: int
    functions: int
    classes: int
    issues: int
    open_issues: int
    security_findings: int


class QualitySection(BaseModel):
    issues_by_severity: dict[str, int]
    issues_by_category: dict[str, int]
    issues_by_status: dict[str, int]
    top_rules: list[RuleCount]


class ComplexityFile(BaseModel):
    path: str
    max_complexity: int
    avg_complexity: float
    functions: int


class DistributionBucket(BaseModel):
    label: str
    files: int


class ComplexitySection(BaseModel):
    avg_cyclomatic: float
    max_cyclomatic: int
    distribution: list[DistributionBucket]
    most_complex_files: list[ComplexityFile]


class SecuritySection(BaseModel):
    label: str = "Static Security Checks"
    disclaimer: str = (
        "Lightweight pattern and AST checks. This is not a complete security audit "
        "and cannot find every vulnerability."
    )
    total: int
    by_severity: dict[str, int]
    by_rule: list[RuleCount]


class LanguageStat(BaseModel):
    language: str
    files: int
    lines: int


class DirectoryStat(BaseModel):
    name: str
    files: int
    lines: int


class LargeFile(BaseModel):
    path: str
    lines_of_code: int
    functions: int


class ArchitectureSection(BaseModel):
    languages: list[LanguageStat]
    directories: list[DirectoryStat]
    largest_files: list[LargeFile]


class ReportResponse(BaseModel):
    analysis: AnalysisResponse
    overview: OverviewCards
    scores: ScoresResponse | None
    score_explanation: str
    quality: QualitySection
    complexity: ComplexitySection
    security: SecuritySection
    architecture: ArchitectureSection
    ai_summary: str | None
    ai_summary_label: str = "Automated summary, generated from the structured results above"


# ------------------------------------------------------------------- files
class FileResponse(BaseModel):
    path: str
    language: str
    lines_of_code: int
    function_count: int
    class_count: int
    import_count: int
    max_complexity: int
    avg_complexity: float
    issue_count: int


class FilePage(BaseModel):
    items: list[FileResponse]
    total: int
    limit: int
    offset: int


# ----------------------------------------------------------------- history
class HistoryPoint(BaseModel):
    analysis_id: int
    number: int            # "Analysis #3"
    date: datetime
    branch: str | None
    commit_sha: str | None
    overall: float
    code_quality: float
    maintainability: float
    complexity: float
    security: float
    issue_count: int
    security_finding_count: int
    avg_complexity: float


# ---------------------------------------------------------------- insights
class ClusterResponse(BaseModel):
    label: str
    size: int
    highest_severity: str
    rule_ids: list[str]
    top_terms: list[str]
    top_files: list[str]
    sample_ids: list[int]


class InsightsResponse(BaseModel):
    label: str = "AI-assisted analysis"
    method: str = (
        "Rule-based summaries and local TF-IDF clustering of finding descriptions. "
        "No source code is sent to any external service."
    )
    summary: str | None
    recommendations: list[str]
    issue_clusters: list[ClusterResponse]
    security_clusters: list[ClusterResponse]
    clustered_issue_count: int
    truncated: bool
