from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.asset import AssetRead, AssetRegisterRequest
from app.services.asset_service import AssetService

router = APIRouter()


@router.post("", response_model=AssetRead)
def register_asset(payload: AssetRegisterRequest, db: Session = Depends(get_db)):
    service = AssetService(db)
    try:
        asset = service.register_asset(payload)
        return asset
    except ValueError as exc:
        if str(exc) in {"project_not_found", "sequence_not_found"}:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise


@router.post("/register", response_model=dict)
def register_asset_with_upload_target(payload: AssetRegisterRequest, db: Session = Depends(get_db)) -> dict:
    service = AssetService(db)
    try:
        asset, upload_target = service.register_asset_with_target(payload)
        return {"asset": AssetRead.model_validate(asset), "upload_target": upload_target}
    except ValueError as exc:
        if str(exc) in {"project_not_found", "sequence_not_found"}:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise


@router.get("/project/{project_id}", response_model=list[AssetRead])
def list_assets(project_id: UUID, db: Session = Depends(get_db)) -> list[AssetRead]:
    service = AssetService(db)
    return [AssetRead.model_validate(item) for item in service.list_assets(project_id)]
