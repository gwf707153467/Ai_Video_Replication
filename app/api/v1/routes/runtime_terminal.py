from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    CompleteJobRequest,
    CompleteJobResult,
    FailJobRequest,
    FailJobResult,
    RuntimeJobTerminalView,
    RuntimeTerminalErrorResponse,
)
from app.services.runtime_errors import RuntimeLeaseConflictError, RuntimeStateConflictError
from app.services.runtime_terminal_facade import RuntimeTerminalFacade

router = APIRouter()


def _build_terminal_error_response(
    *,
    detail: str,
    error_type: str,
    job_id: str | None = None,
    attempt_id: str | None = None,
    worker_id: str | None = None,
    claim_token: str | None = None,
) -> RuntimeTerminalErrorResponse:
    return RuntimeTerminalErrorResponse(
        detail=detail,
        error_type=error_type,
        job_id=job_id,
        attempt_id=attempt_id,
        worker_id=worker_id,
        claim_token=claim_token,
    )


def _terminal_error_json_response(
    *,
    status_code: int,
    detail: str,
    error_type: str,
    job_id: str | None = None,
    attempt_id: str | None = None,
    worker_id: str | None = None,
    claim_token: str | None = None,
) -> JSONResponse:
    body = _build_terminal_error_response(
        detail=detail,
        error_type=error_type,
        job_id=job_id,
        attempt_id=attempt_id,
        worker_id=worker_id,
        claim_token=claim_token,
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body)


@router.get(
    "/jobs/{job_id}",
    response_model=RuntimeJobTerminalView,
    responses={404: {"model": RuntimeTerminalErrorResponse}},
)
def get_terminal_job(job_id: str, db: Session = Depends(get_db)) -> RuntimeJobTerminalView | JSONResponse:
    facade = RuntimeTerminalFacade(db)
    view = facade.get_terminal_view(job_id)
    if view is None:
        return _terminal_error_json_response(
            status_code=404,
            detail=f"job not found: {job_id}",
            error_type="runtime_job_not_found",
            job_id=job_id,
        )
    return view


@router.post(
    "/complete",
    response_model=CompleteJobResult,
    responses={409: {"model": RuntimeTerminalErrorResponse}},
)
def complete_job(payload: CompleteJobRequest, db: Session = Depends(get_db)) -> CompleteJobResult | JSONResponse:
    facade = RuntimeTerminalFacade(db)
    try:
        return facade.complete_job(payload)
    except RuntimeLeaseConflictError as exc:
        return _terminal_error_json_response(
            status_code=409,
            detail=str(exc),
            error_type="runtime_lease_conflict",
            job_id=payload.job_id,
            attempt_id=payload.attempt_id,
            worker_id=payload.worker_id,
            claim_token=payload.claim_token,
        )
    except RuntimeStateConflictError as exc:
        return _terminal_error_json_response(
            status_code=409,
            detail=str(exc),
            error_type="runtime_state_conflict",
            job_id=payload.job_id,
            attempt_id=payload.attempt_id,
            worker_id=payload.worker_id,
            claim_token=payload.claim_token,
        )


@router.post(
    "/fail",
    response_model=FailJobResult,
    responses={409: {"model": RuntimeTerminalErrorResponse}},
)
def fail_job(payload: FailJobRequest, db: Session = Depends(get_db)) -> FailJobResult | JSONResponse:
    facade = RuntimeTerminalFacade(db)
    try:
        return facade.fail_job(payload)
    except RuntimeLeaseConflictError as exc:
        return _terminal_error_json_response(
            status_code=409,
            detail=str(exc),
            error_type="runtime_lease_conflict",
            job_id=payload.job_id,
            attempt_id=payload.attempt_id,
            worker_id=payload.worker_id,
            claim_token=payload.claim_token,
        )
    except RuntimeStateConflictError as exc:
        return _terminal_error_json_response(
            status_code=409,
            detail=str(exc),
            error_type="runtime_state_conflict",
            job_id=payload.job_id,
            attempt_id=payload.attempt_id,
            worker_id=payload.worker_id,
            claim_token=payload.claim_token,
        )
