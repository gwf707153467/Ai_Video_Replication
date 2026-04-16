from fastapi import APIRouter, HTTPException
from minio.error import S3Error

from app.schemas.storage import StorageBootstrapResponse
from app.services.storage_service import StorageService

router = APIRouter()


@router.post("/bootstrap", response_model=StorageBootstrapResponse)
def bootstrap_storage() -> StorageBootstrapResponse:
    service = StorageService()
    try:
        return service.ensure_buckets()
    except S3Error as exc:
        raise HTTPException(status_code=500, detail=f"storage_bootstrap_failed:{exc.code}") from exc
