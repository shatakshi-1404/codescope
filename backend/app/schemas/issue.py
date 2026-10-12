from pydantic import BaseModel

from app.models import IssueStatus


class IssueStatusUpdate(BaseModel):
    status: IssueStatus
