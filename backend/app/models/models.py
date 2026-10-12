import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------- Enums (stored as plain strings, easy to migrate) ----------
class Role(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


def _enum(e):
    return Enum(e, native_enum=False, length=20)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---------- Tables ----------
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)

    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMember(TimestampMixin, Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[Role] = mapped_column(_enum(Role))

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Repository(TimestampMixin, Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("project_id", "url", name="uq_project_repo_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    name: Mapped[str] = mapped_column(String(200))
    default_branch: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str | None] = mapped_column(String(50))

    project: Mapped[Project] = relationship(back_populates="repositories")
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


class Analysis(TimestampMixin, Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    triggered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    branch: Mapped[str | None] = mapped_column(String(200))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[AnalysisStatus] = mapped_column(
        _enum(AnalysisStatus), default=AnalysisStatus.PENDING, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # summary numbers shown on the report header cards
    files_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    lines_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    function_count: Mapped[int] = mapped_column(Integer, default=0)
    class_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    skipped_files: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    warnings_text: Mapped[str | None] = mapped_column(Text)

    repository: Mapped[Repository] = relationship(back_populates="analyses")
    files: Mapped[list["AnalysisFile"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    security_findings: Mapped[list["SecurityFinding"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    metrics: Mapped["QualityMetric | None"] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", uselist=False
    )


class AnalysisFile(Base):
    __tablename__ = "analysis_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(30))
    lines_of_code: Mapped[int] = mapped_column(Integer, default=0)
    function_count: Mapped[int] = mapped_column(Integer, default=0)
    class_count: Mapped[int] = mapped_column(Integer, default=0)
    import_count: Mapped[int] = mapped_column(Integer, default=0)
    max_complexity: Mapped[int] = mapped_column(Integer, default=0)
    avg_complexity: Mapped[float] = mapped_column(Float, default=0.0)

    analysis: Mapped[Analysis] = relationship(back_populates="files")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (Index("ix_issues_analysis_status", "analysis_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(60))
    file: Mapped[str] = mapped_column(String(1000))
    line: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[Severity] = mapped_column(_enum(Severity), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    status: Mapped[IssueStatus] = mapped_column(_enum(IssueStatus), default=IssueStatus.OPEN)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped[Analysis] = relationship(back_populates="issues")


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(60))
    file: Mapped[str] = mapped_column(String(1000))
    line: Mapped[int] = mapped_column(Integer)
    severity: Mapped[Severity] = mapped_column(_enum(Severity), index=True)
    description: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)

    analysis: Mapped[Analysis] = relationship(back_populates="security_findings")


class QualityMetric(Base):
    __tablename__ = "quality_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), unique=True
    )
    overall_score: Mapped[float] = mapped_column(Float)
    code_quality_score: Mapped[float] = mapped_column(Float)
    maintainability_score: Mapped[float] = mapped_column(Float)
    complexity_score: Mapped[float] = mapped_column(Float)
    security_score: Mapped[float] = mapped_column(Float)
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    security_finding_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_complexity: Mapped[float] = mapped_column(Float, default=0.0)

    analysis: Mapped[Analysis] = relationship(back_populates="metrics")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_project_created", "project_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User | None] = relationship()
