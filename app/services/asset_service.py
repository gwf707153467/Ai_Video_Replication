from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Asset, Project, Sequence
from app.schemas.asset import AssetRegisterRequest, AssetUploadTarget
from app.services.asset_policy_service import AssetPolicyService
from app.services.storage_service import StorageService


class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.storage_service = StorageService()

    @staticmethod
    def _safe_name(filename: str | None) -> str:
        return AssetPolicyService.safe_name(filename)

    def _resolve_bucket(self, asset_type: str) -> str:
        return AssetPolicyService.resolve_bucket(asset_type)

    def _build_object_key(self, payload: AssetRegisterRequest) -> str:
        return AssetPolicyService.build_project_asset_object_key(
            project_id=payload.project_id,
            sequence_id=payload.sequence_id,
            asset_type=payload.asset_type,
            asset_role=payload.asset_role,
            source_filename=payload.source_filename,
        )

    def register_asset(self, payload: AssetRegisterRequest) -> Asset:
        project = self.db.get(Project, payload.project_id)
        if not project:
            raise ValueError("project_not_found")

        if payload.sequence_id:
            sequence = self.db.get(Sequence, payload.sequence_id)
            if not sequence or sequence.project_id != payload.project_id:
                raise ValueError("sequence_not_found")

        bucket_name = self._resolve_bucket(payload.asset_type)
        object_key = payload.object_key or self._build_object_key(payload)

        asset = Asset(
            project_id=payload.project_id,
            sequence_id=payload.sequence_id,
            asset_type=payload.asset_type,
            asset_role=payload.asset_role,
            bucket_name=bucket_name,
            object_key=object_key,
            source_filename=payload.source_filename,
            content_type=payload.content_type,
            file_size=payload.file_size,
            asset_metadata=payload.asset_metadata,
            notes=payload.notes,
            status="registered",
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def register_asset_with_target(self, payload: AssetRegisterRequest) -> tuple[Asset, AssetUploadTarget]:
        asset = self.register_asset(payload)
        target = AssetUploadTarget(
            bucket_name=asset.bucket_name,
            object_key=asset.object_key,
            upload_path=f"s3://{asset.bucket_name}/{asset.object_key}",
        )
        return asset, target

    def list_assets(self, project_id: UUID) -> list[Asset]:
        return (
            self.db.query(Asset)
            .filter(Asset.project_id == project_id)
            .order_by(Asset.created_at.asc())
            .all()
        )
