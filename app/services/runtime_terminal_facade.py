from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import JobAttemptRepository, RuntimeJobRepository, WorkerLeaseRepository
from app.schemas.runtime import (
    CompleteJobRequest,
    CompleteJobResult,
    FailJobRequest,
    FailJobResult,
    RuntimeJobTerminalAttemptView,
    RuntimeJobTerminalLeaseView,
    RuntimeJobTerminalView,
)
from app.services.runtime_complete_service import RuntimeCompleteService
from app.services.runtime_fail_service import RuntimeFailService


class RuntimeTerminalFacade:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.runtime_jobs = RuntimeJobRepository(db)
        self.job_attempts = JobAttemptRepository(db)
        self.worker_leases = WorkerLeaseRepository(db)
        self.runtime_complete_service = RuntimeCompleteService(db)
        self.runtime_fail_service = RuntimeFailService(db)

    def complete_job(self, request: CompleteJobRequest) -> CompleteJobResult:
        return self.runtime_complete_service.complete_job(request)

    def fail_job(self, request: FailJobRequest) -> FailJobResult:
        return self.runtime_fail_service.fail_job(request)

    def get_terminal_view(self, job_id: str) -> RuntimeJobTerminalView | None:
        job = self.runtime_jobs.get_by_job_id(job_id)
        if job is None:
            return None

        attempt = self.job_attempts.get_latest_attempt(job_id)
        lease = self.worker_leases.get_active_lease_by_job_id(job_id)

        attempt_view = None
        if attempt is not None:
            attempt_view = RuntimeJobTerminalAttemptView(
                attempt_id=attempt.attempt_id,
                attempt_status=attempt.attempt_status,
                attempt_index=attempt.attempt_index,
                worker_id=attempt.worker_id,
                claim_token=attempt.claim_token,
                started_at=attempt.started_at,
                finished_at=attempt.finished_at,
                completion_status=attempt.completion_status,
                error_code=attempt.error_code,
                error_message=attempt.error_message,
                error_payload_json=attempt.error_payload_json,
                result_ref=attempt.result_ref,
                manifest_artifact_id=attempt.manifest_artifact_id,
                runtime_ms=attempt.runtime_ms,
                provider_runtime_ms=attempt.provider_runtime_ms,
                upload_ms=attempt.upload_ms,
                metrics_json=attempt.metrics_json,
                metadata_json=attempt.metadata_json,
            )

        lease_view = None
        if lease is not None:
            lease_view = RuntimeJobTerminalLeaseView(
                lease_id=lease.lease_id,
                job_id=lease.job_id,
                attempt_id=lease.attempt_id,
                worker_id=lease.worker_id,
                claim_token=lease.claim_token,
                lease_status=lease.lease_status,
                lease_started_at=lease.lease_started_at,
                lease_expires_at=lease.lease_expires_at,
                last_heartbeat_at=lease.last_heartbeat_at,
                heartbeat_count=lease.heartbeat_count,
                extension_count=lease.extension_count,
                revoked_at=lease.revoked_at,
                revoked_reason=lease.revoked_reason,
                metadata_json=lease.metadata_json,
            )

        return RuntimeJobTerminalView(
            job_id=job.job_id,
            job_status=job.job_status,
            claimed_by_worker_id=job.claimed_by_worker_id,
            active_claim_token=job.active_claim_token,
            attempt_count=job.attempt_count,
            queued_at=job.queued_at,
            claimed_at=job.claimed_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            lease_expires_at=job.lease_expires_at,
            terminal_reason_code=job.terminal_reason_code,
            terminal_reason_message=job.terminal_reason_message,
            metadata_json=job.metadata_json,
            latest_attempt=attempt_view,
            active_lease=lease_view,
        )
