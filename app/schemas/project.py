from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ProjectCreate(BaseModel):
    name: str
    status: str = "draft"
    source_market: str = "US"
    source_language: str = "en-US"
    notes: str | None = None


class ProjectRead(ORMModel):
    id: UUID
    name: str
    status: str
    source_market: str
    source_language: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
