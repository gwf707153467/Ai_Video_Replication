from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class VBUCreate(BaseModel):
    project_id: UUID
    sequence_id: UUID | None = None
    vbu_code: str
    persuasive_role: str = "benefit"
    script_text: str
    voice_profile: str | None = None
    language: str = "en-US"
    duration_ms: int | None = None
    tts_params: dict = Field(default_factory=dict)
    status: str = "draft"


class VBURead(ORMModel):
    id: UUID
    project_id: UUID
    sequence_id: UUID | None = None
    vbu_code: str
    persuasive_role: str
    script_text: str
    voice_profile: str | None = None
    language: str
    duration_ms: int | None = None
    tts_params: dict
    status: str
    created_at: datetime
