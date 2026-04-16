from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.compilers.orchestrator.compiler_service import CompilerService
from app.db.models import CompiledRuntime
from app.db.session import get_db
from app.schemas import CompileRequest, CompileValidationRead, CompiledRuntimeRead

router = APIRouter()


@router.post("", response_model=CompiledRuntimeRead)
def compile_runtime(payload: CompileRequest, db: Session = Depends(get_db)) -> CompiledRuntime:
    service = CompilerService(db)
    try:
        return service.compile_project(payload)
    except ValueError as exc:
        if str(exc) == "project_not_found":
            raise HTTPException(status_code=404, detail="project_not_found") from exc
        if str(exc) == "project_invalid":
            raise HTTPException(status_code=422, detail="project_invalid") from exc
        raise


@router.get("/validate/{project_id}", response_model=CompileValidationRead)
def validate_compile_project(project_id: UUID, db: Session = Depends(get_db)) -> CompileValidationRead:
    service = CompilerService(db)
    try:
        result = service.validate_project(project_id)
        return CompileValidationRead(**result)
    except ValueError as exc:
        if str(exc) == "project_not_found":
            raise HTTPException(status_code=404, detail="project_not_found") from exc
        raise
