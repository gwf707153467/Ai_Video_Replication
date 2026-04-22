from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from minio.error import S3Error

from app.services.storage_service import StorageService


@dataclass
class MaterializedObject:
    bucket_name: str
    object_key: str
    etag: str | None = None
    version_id: str | None = None
    size: int | None = None
    content_type: str | None = None


class RuntimeArtifactService:
    def __init__(self) -> None:
        self.storage_service = StorageService()

    def object_exists(self, bucket_name: str, object_key: str) -> bool:
        return self.storage_service.object_exists(bucket_name, object_key)

    def stat_object(self, bucket_name: str, object_key: str) -> MaterializedObject | None:
        stat = self.storage_service.stat_object(bucket_name, object_key)
        if not stat:
            return None
        return MaterializedObject(
            bucket_name=bucket_name,
            object_key=object_key,
            etag=getattr(stat, "etag", None),
            version_id=getattr(stat, "version_id", None),
            size=getattr(stat, "size", None),
            content_type=getattr(stat, "content_type", None),
        )

    def materialize_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
        payload: bytes,
        content_type: str,
    ) -> MaterializedObject:
        result = self.storage_service.put_bytes(
            bucket_name=bucket_name,
            object_key=object_key,
            payload=payload,
            content_type=content_type,
        )
        return MaterializedObject(
            bucket_name=bucket_name,
            object_key=object_key,
            etag=getattr(result, "etag", None),
            version_id=getattr(result, "version_id", None),
            size=len(payload),
            content_type=content_type,
        )

    def materialize_text(
        self,
        *,
        bucket_name: str,
        object_key: str,
        text: str,
        content_type: str = "text/plain; charset=utf-8",
    ) -> MaterializedObject:
        return self.materialize_bytes(
            bucket_name=bucket_name,
            object_key=object_key,
            payload=text.encode("utf-8"),
            content_type=content_type,
        )

    def get_bytes(self, bucket_name: str, object_key: str) -> bytes:
        return self.storage_service.get_bytes(bucket_name, object_key)
