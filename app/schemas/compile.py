from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CompileRequest(BaseModel):
    project_id: UUID
    runtime_version: str | None = None
    compile_reason: str = "manual"
    compile_options: dict = Field(default_factory=dict)
    auto_version: bool = True
    dispatch_jobs: bool = False


class RuntimeSequencePacket(BaseModel):
    sequence_id: UUID
    sequence_index: int
    sequence_type: str
    persuasive_goal: str | None = None
    spus: list[dict] = Field(default_factory=list)
    vbus: list[dict] = Field(default_factory=list)
    bridges: list[dict] = Field(default_factory=list)


class RuntimePacket(BaseModel):
    project_id: UUID
    runtime_version: str
    compile_reason: str
    compile_options: dict
    visual_track_count: int
    audio_track_count: int
    bridge_count: int
    sequences: list[RuntimeSequencePacket]


class CompileValidationRead(BaseModel):
    project_id: UUID
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    counts: dict = Field(default_factory=dict)


class CompiledRuntimeRead(ORMModel):
    id: UUID
    project_id: UUID
    runtime_version: str
    compile_status: str
    runtime_payload: dict
    dispatch_status: str
    dispatch_summary: dict
    last_error_code: str | None = None
    last_error_message: str | None = None
    compile_started_at: datetime | None = None
    compile_finished_at: datetime | None = None
    created_at: datetime
