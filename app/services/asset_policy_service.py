from pathlib import Path
from uuid import UUID

from app.services.storage_service import StorageService


class AssetPolicyService:
    @staticmethod
    def safe_name(filename: str | None) -> str:
        if not filename:
            return "asset.bin"
        return Path(filename).name.replace(" ", "_")

    @staticmethod
    def resolve_bucket(asset_type: str) -> str:
        bucket_map = StorageService.bucket_map()
        if asset_type in {"reference_video", "reference_image"}:
            return bucket_map["reference"]
        if asset_type == "generated_image":
            return bucket_map["generated_images"]
        if asset_type == "generated_video":
            return bucket_map["generated_videos"]
        if asset_type == "audio":
            return bucket_map["audio"]
        if asset_type == "runtime":
            return bucket_map["runtime"]
        if asset_type == "export":
            return bucket_map["exports"]
        return bucket_map["reference"]

    @classmethod
    def build_project_asset_object_key(
        cls,
        *,
        project_id: UUID,
        asset_type: str,
        asset_role: str,
        source_filename: str | None,
        sequence_id: UUID | None = None,
    ) -> str:
        filename = cls.safe_name(source_filename)
        sequence_scope = f"sequences/{sequence_id}" if sequence_id else "project"
        return f"projects/{project_id}/{sequence_scope}/{asset_type}/{asset_role}/{filename}"

    @classmethod
    def build_runtime_asset_object_key(
        cls,
        *,
        project_id: UUID,
        runtime_version: str,
        job_type: str,
        filename: str | None,
    ) -> str:
        safe_filename = cls.safe_name(filename)
        return f"projects/{project_id}/runtime/{runtime_version}/{job_type}/{safe_filename}"
