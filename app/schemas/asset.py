from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AssetCreate(BaseModel):
    project_id: UUID
    sequence_id: UUID | None = None
    asset_type: str
    asset_role: str
    source_filename: str | None = None
    content_type: str | None = None
    file_size: int | None = None
    asset_metadata: dict = Field(default_factory=dict)
    notes: str | None = None


class AssetRegisterRequest(AssetCreate):
    object_key: str | None = None


class AssetUploadTarget(BaseModel):
    bucket_name: str
    object_key: str
    upload_path: str


class AssetRead(ORMModel):
    id: UUID
    project_id: UUID
    sequence_id: UUID | None = None
    asset_type: str
    asset_role: str
    bucket_name: str
    object_key: str
    source_filename: str | None = None
    content_type: str | None = None
    file_size: int | None = None
    asset_metadata: dict
    status: str
    notes: str | None = None
    created_at: datetime
