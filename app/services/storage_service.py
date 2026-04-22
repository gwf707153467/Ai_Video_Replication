from io import BytesIO

from minio.datatypes import Object
from minio.error import S3Error

from app.core.config import settings
from app.schemas.storage import BucketStatus, StorageBootstrapResponse
from app.storage.minio_client import get_minio_client


class StorageService:
    def __init__(self) -> None:
        self.client = get_minio_client()

    @staticmethod
    def bucket_map() -> dict[str, str]:
        return {
            "reference": settings.minio_bucket_reference,
            "generated_images": settings.minio_bucket_generated_images,
            "generated_videos": settings.minio_bucket_generated_videos,
            "audio": settings.minio_bucket_audio,
            "exports": settings.minio_bucket_exports,
            "runtime": settings.minio_bucket_runtime,
        }

    def ensure_buckets(self) -> StorageBootstrapResponse:
        statuses: list[BucketStatus] = []
        for bucket_name in self.bucket_map().values():
            exists = self.client.bucket_exists(bucket_name)
            if not exists:
                self.client.make_bucket(bucket_name)
                exists = True
            statuses.append(BucketStatus(bucket_name=bucket_name, exists=exists))
        return StorageBootstrapResponse(buckets=statuses)

    def bucket_exists(self, bucket_name: str) -> bool:
        try:
            return self.client.bucket_exists(bucket_name)
        except S3Error:
            return False

    def stat_object(self, bucket_name: str, object_key: str) -> Object | None:
        try:
            return self.client.stat_object(bucket_name, object_key)
        except S3Error as exc:
            if getattr(exc, "code", None) in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return None
            raise

    def object_exists(self, bucket_name: str, object_key: str) -> bool:
        return self.stat_object(bucket_name, object_key) is not None

    def put_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
        payload: bytes,
        content_type: str,
    ):
        return self.client.put_object(
            bucket_name=bucket_name,
            object_name=object_key,
            data=BytesIO(payload),
            length=len(payload),
            content_type=content_type,
        )

    def get_bytes(self, bucket_name: str, object_key: str) -> bytes:
        response = self.client.get_object(bucket_name, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
