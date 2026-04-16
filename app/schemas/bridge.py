from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class BridgeCreate(BaseModel):
    project_id: UUID
    sequence_id: UUID
    spu_id: UUID | None = None
    vbu_id: UUID | None = None
    bridge_code: str
    bridge_type: str = "sequence_unit_binding"
    execution_order: int = 0
    transition_policy: dict = Field(default_factory=dict)
    status: str = "draft"


class BridgeRead(ORMModel):
    id: UUID
    project_id: UUID
    sequence_id: UUID
    spu_id: UUID | None = None
    vbu_id: UUID | None = None
    bridge_code: str
    bridge_type: str
    execution_order: int
    transition_policy: dict
    status: str
    created_at: datetime
