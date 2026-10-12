from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import Role


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class ProjectResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    my_role: Role  # the caller's role in this project, so the UI can hide buttons


class MemberInvite(BaseModel):
    email: EmailStr
    role: Role = Role.MEMBER


class MemberRoleUpdate(BaseModel):
    role: Role


class MemberResponse(BaseModel):
    id: int          # project_members.id
    user_id: int
    name: str
    email: EmailStr
    role: Role
    created_at: datetime
