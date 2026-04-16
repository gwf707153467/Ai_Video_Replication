from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from .errors import (
    RuntimeTerminalConflictError,
    RuntimeTerminalError,
    RuntimeTerminalNotFoundError,
    RuntimeTerminalServerError,
    RuntimeTerminalTransportError,
    RuntimeTerminalValidationError,
)
from .models import RuntimeAttemptContext


class RuntimeTerminalClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 10.0,
        session: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or httpx.Client()

    def complete_job(
        self,
        ctx: RuntimeAttemptContext,
        *,
        completion_status: str | None = None,
        terminal_reason: str | None = None,
        result_ref: str | None = None,
        manifest_artifact_id: UUID | str | None = None,
        runtime_ms: int | None = None,
        provider_runtime_ms: int | None = None,
        upload_ms: int | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "job_id": ctx.job_id,
            "attempt_id": ctx.attempt_id,
            "worker_id": ctx.worker_id,
            "claim_token": ctx.claim_token,
            "completion_status": completion_status,
            "terminal_reason": terminal_reason,
            "result_ref": result_ref,
            "manifest_artifact_id": str(manifest_artifact_id) if manifest_artifact_id is not None else None,
            "runtime_ms": runtime_ms,
            "provider_runtime_ms": provider_runtime_ms,
            "upload_ms": upload_ms,
            "metadata_json": metadata_json,
        }
        return self._request("POST", "/api/v1/runtime/terminal/complete", json=payload)

    def fail_job(
        self,
        ctx: RuntimeAttemptContext,
        *,
        next_job_status: str,
        attempt_terminal_status: str,
        terminal_reason: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        error_payload_json: dict[str, Any] | None = None,
        expire_lease: bool = False,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "job_id": ctx.job_id,
            "attempt_id": ctx.attempt_id,
            "worker_id": ctx.worker_id,
            "claim_token": ctx.claim_token,
            "next_job_status": next_job_status,
            "attempt_terminal_status": attempt_terminal_status,
            "terminal_reason": terminal_reason,
            "error_code": error_code,
            "error_message": error_message,
            "error_payload_json": error_payload_json,
            "expire_lease": expire_lease,
            "metadata_json": metadata_json,
        }
        return self._request("POST", "/api/v1/runtime/terminal/fail", json=payload)

    def get_job_snapshot(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/runtime/terminal/jobs/{job_id}")

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise RuntimeTerminalTransportError(
                "runtime terminal transport failure",
                method=method,
                path=path,
            ) from exc

        if response.status_code == 404:
            raise RuntimeTerminalNotFoundError(
                "runtime terminal resource not found",
                status_code=404,
                method=method,
                path=path,
                response_text=response.text,
            )
        if response.status_code == 409:
            raise RuntimeTerminalConflictError(
                "runtime terminal state or attempt-context conflict",
                status_code=409,
                method=method,
                path=path,
                response_text=response.text,
            )
        if response.status_code == 422:
            raise RuntimeTerminalValidationError(
                "runtime terminal validation error",
                status_code=422,
                method=method,
                path=path,
                response_text=response.text,
            )
        if response.status_code >= 500:
            raise RuntimeTerminalServerError(
                "runtime terminal server error",
                status_code=response.status_code,
                method=method,
                path=path,
                response_text=response.text,
            )
        if response.status_code >= 400:
            raise RuntimeTerminalError(
                "runtime terminal unexpected http error",
                status_code=response.status_code,
                method=method,
                path=path,
                response_text=response.text,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeTerminalServerError(
                "runtime terminal returned a non-json success response",
                status_code=response.status_code,
                method=method,
                path=path,
                response_text=response.text,
            ) from exc
