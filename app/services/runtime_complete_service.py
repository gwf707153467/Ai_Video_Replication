from __future__ import annotations

from sqlalchemy.orm import Session

from app.enums.runtime import AttemptStatus, JobStatus
from app.repositories import (
    JobAttemptRepository,
    RuntimeJobRepository,
    WorkerLeaseRepository,
    WorkerRegistryRepository,
)
from app.schemas.runtime import CompleteJobRequest, CompleteJobResult
from app.services.runtime_errors import RuntimeLeaseConflictError, RuntimeStateConflictError


class RuntimeCompleteService:
    ACTIVE_ATTEMPT_STATUSES = {
        AttemptStatus.CLAIMED.value,
        AttemptStatus.STARTED.value,
        AttemptStatus.PROVIDER_RUNNING.value,
        AttemptStatus.ARTIFACT_COLLECTING.value,
    }
    TERMINAL_JOB_STATUSES = {
        JobStatus.SUCCEEDED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
        JobStatus.SUPERSEDED.value,
        JobStatus.STALE.value,
        JobStatus.DEAD_LETTERED.value,
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.runtime_jobs = RuntimeJobRepository(db)
        self.job_attempts = JobAttemptRepository(db)
        self.worker_leases = WorkerLeaseRepository(db)
        self.worker_registry = WorkerRegistryRepository(db)

    def complete_job(self, request: CompleteJobRequest) -> CompleteJobResult:
        now = self.runtime_jobs.utcnow()
        manifest_artifact_id = (
            str(request.manifest_artifact_id) if request.manifest_artifact_id is not None else None
        )

        with self.db.begin():
            try:
                lease = self.worker_leases.get_active_lease_by_claim_token(request.claim_token, for_update=True)
                if lease is None:
                    raise RuntimeLeaseConflictError(
                        f"active lease not found for claim_token={request.claim_token}"
                    )
                self._assert_lease_matches(lease=lease, request=request)

                job = self.runtime_jobs.get_by_job_id(request.job_id, for_update=True)
                if job is None:
                    raise RuntimeStateConflictError(f"job not found: {request.job_id}")
                self._assert_active_claim(job=job, request=request)
                if job.job_status in self.TERMINAL_JOB_STATUSES:
                    raise RuntimeStateConflictError(
                        f"job {job.job_id} already terminal: {job.job_status}"
                    )

                attempt = self.job_attempts.get_attempt_by_attempt_id(request.attempt_id, for_update=True)
                if attempt is None:
                    raise RuntimeStateConflictError(f"attempt not found: {request.attempt_id}")
                self._assert_attempt_matches(attempt=attempt, request=request)
                if attempt.attempt_status not in self.ACTIVE_ATTEMPT_STATUSES:
                    raise RuntimeStateConflictError(
                        f"attempt {attempt.attempt_id} cannot complete from {attempt.attempt_status}"
                    )

                attempt = self.job_attempts.mark_completed(
                    attempt_id=request.attempt_id,
                    completion_status=request.completion_status or JobStatus.SUCCEEDED.value,
                    finished_at=now,
                    result_ref=request.result_ref,
                    manifest_artifact_id=manifest_artifact_id,
                    runtime_ms=request.runtime_ms,
                    provider_runtime_ms=request.provider_runtime_ms,
                    upload_ms=request.upload_ms,
                )
                job = self.runtime_jobs.mark_succeeded(
                    job_id=request.job_id,
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    finished_at=now,
                    terminal_reason_code=request.completion_status or JobStatus.SUCCEEDED.value,
                    terminal_reason_message=request.terminal_reason,
                )
                lease = self.worker_leases.release_lease(
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    released_at=now,
                )
                worker = self.worker_registry.decrement_current_job_count(request.worker_id)
                self.worker_registry.mark_seen(request.worker_id, seen_at=now)

                # TODO(runtime-events): append job_events after event repository is available.
                return CompleteJobResult(
                    job_id=job.job_id,
                    attempt_id=attempt.attempt_id,
                    lease_id=lease.lease_id,
                    job_status=job.job_status,
                    attempt_status=attempt.attempt_status,
                    lease_status=lease.lease_status,
                    worker_id=request.worker_id,
                    current_job_count=worker.current_job_count,
                    finished_at=job.finished_at or attempt.finished_at or now,
                    metadata_json=request.metadata_json,
                )
            except ValueError as exc:
                raise self._map_repository_value_error(exc) from exc

    @staticmethod
    def _assert_lease_matches(*, lease, request: CompleteJobRequest) -> None:
        if lease.job_id != request.job_id:
            raise RuntimeLeaseConflictError("lease.job_id mismatch")
        if lease.worker_id != request.worker_id:
            raise RuntimeLeaseConflictError("lease.worker_id mismatch")
        if lease.attempt_id != request.attempt_id:
            raise RuntimeLeaseConflictError("lease.attempt_id mismatch")

    @staticmethod
    def _assert_active_claim(*, job, request: CompleteJobRequest) -> None:
        if job.active_claim_token != request.claim_token:
            raise RuntimeLeaseConflictError("job.active_claim_token mismatch")
        if job.claimed_by_worker_id != request.worker_id:
            raise RuntimeLeaseConflictError("job.claimed_by_worker_id mismatch")

    @staticmethod
    def _assert_attempt_matches(*, attempt, request: CompleteJobRequest) -> None:
        if attempt.job_id != request.job_id:
            raise RuntimeLeaseConflictError("attempt.job_id mismatch")
        if attempt.claim_token != request.claim_token:
            raise RuntimeLeaseConflictError("attempt.claim_token mismatch")
        if attempt.worker_id != request.worker_id:
            raise RuntimeLeaseConflictError("attempt.worker_id mismatch")

    @staticmethod
    def _map_repository_value_error(exc: ValueError) -> RuntimeLeaseConflictError | RuntimeStateConflictError:
        message = str(exc)
        if (
            message.startswith("active lease not found")
            or message.startswith("lease ")
            or "claim_token mismatch" in message
            or "claimed_by_worker_id mismatch" in message
            or "worker_id mismatch" in message
            or message == "lease.job_id mismatch"
            or message == "lease.worker_id mismatch"
            or message == "lease.attempt_id mismatch"
            or message == "attempt.job_id mismatch"
        ):
            return RuntimeLeaseConflictError(message)
        return RuntimeStateConflictError(message)
