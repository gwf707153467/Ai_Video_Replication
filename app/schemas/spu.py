from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class SPUCreate(BaseModel):
    project_id: UUID
    sequence_id: UUID | None = None
    spu_code: str
    display_name: str
    asset_role: str = "primary_visual"
    duration_ms: int = 5000
    generation_mode: str = "veo_segment"
    prompt_text: str | None = None
    negative_prompt_text: str | None = None
    visual_constraints: dict = Field(default_factory=dict)
    status: str = "draft"


class SPURead(ORMModel):
    id: UUID
    project_id: UUID
    sequence_id: UUID | None = None
    spu_code: str
    display_name: str
    asset_role: str
    duration_ms: int
    generation_mode: str
    prompt_text: str | None = None
    negative_prompt_text: str | None = None
    visual_constraints: dict
    status: str
    created_at: datetime
