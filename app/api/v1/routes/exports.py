from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Job
from app.db.session import get_db
from app.schemas.export import ExportCreate, ExportRead
from app.services.export_service import ExportService

router = APIRouter()


@router.post("", response_model=ExportRead)
def create_export(payload: ExportCreate, db: Session = Depends(get_db)) -> Job:
    service = ExportService(db)
    try:
        return service.create_export_job(payload)
    except ValueError as exc:
        if str(exc) == "project_not_found":
            raise HTTPException(status_code=404, detail="project_not_found") from exc
        if str(exc) == "runtime_not_found":
            raise HTTPException(status_code=404, detail="runtime_not_found") from exc
        raise
