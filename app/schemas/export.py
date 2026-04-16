from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ExportCreate(BaseModel):
    project_id: UUID
    runtime_id: UUID | None = None
    runtime_version: str | None = None
    export_type: str = "final_video"
    provider_name: str | None = None
    export_options: dict = Field(default_factory=dict)


class ExportRead(ORMModel):
    id: UUID
    project_id: UUID
    job_type: str
    status: str
    provider_name: str | None = None
    payload: dict
    result_payload: dict | None = None
    created_at: datetime
