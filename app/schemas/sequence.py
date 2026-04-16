from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class SequenceCreate(BaseModel):
    project_id: UUID
    sequence_index: int
    sequence_type: str
    persuasive_goal: str | None = None
    status: str = "draft"


class SequenceRead(ORMModel):
    id: UUID
    project_id: UUID
    sequence_index: int
    sequence_type: str
    persuasive_goal: str | None = None
    status: str
    created_at: datetime
