from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.enums.runtime import AttemptStatus
from app.models import JobAttempt
from app.repositories.base import BaseRepository
from app.schemas.runtime import JobAttemptCreate


class JobAttemptRepository(BaseRepository):
    def create_attempt(self, payload: JobAttemptCreate) -> JobAttempt:
        attempt = JobAttempt(**payload.model_dump(exclude_none=True))
        self.db.add(attempt)
        self.db.flush()
        return attempt

    def get_latest_attempt(self, job_id: str, *, for_update: bool = False) -> JobAttempt | None:
        stmt = select(JobAttempt).where(JobAttempt.job_id == job_id).order_by(JobAttempt.attempt_index.desc()).limit(1)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def get_attempt_by_attempt_id(self, attempt_id: str, *, for_update: bool = False) -> JobAttempt | None:
        stmt = select(JobAttempt).where(JobAttempt.attempt_id == attempt_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def mark_started(
        self,
        *,
        attempt_id: str,
        claim_token: str | None = None,
        worker_id: str | None = None,
        started_at: datetime | None = None,
    ) -> JobAttempt:
        attempt = self.get_attempt_by_attempt_id(attempt_id, for_update=True)
        if attempt is None:
            raise ValueError(f"attempt not found: {attempt_id}")
        self._assert_attempt_owner(attempt=attempt, claim_token=claim_token, worker_id=worker_id)

        attempt.attempt_status = AttemptStatus.STARTED.value
        attempt.started_at = attempt.started_at or started_at or self.utcnow()
        self.db.flush()
        return attempt

    def mark_provider_running(
        self,
        *,
        attempt_id: str,
        provider_name: str | None = None,
        provider_model: str | None = None,
        provider_run_id: str | None = None,
    ) -> JobAttempt:
        attempt = self.get_attempt_by_attempt_id(attempt_id, for_update=True)
        if attempt is None:
            raise ValueError(f"attempt not found: {attempt_id}")

        attempt.attempt_status = AttemptStatus.PROVIDER_RUNNING.value
        attempt.provider_name = provider_name or attempt.provider_name
        attempt.provider_model = provider_model or attempt.provider_model
        attempt.provider_run_id = provider_run_id or attempt.provider_run_id
        self.db.flush()
        return attempt

    def mark_artifact_collecting(
        self,
        *,
        attempt_id: str,
        result_ref: str | None = None,
        manifest_artifact_id: str | None = None,
    ) -> JobAttempt:
        attempt = self.get_attempt_by_attempt_id(attempt_id, for_update=True)
        if attempt is None:
            raise ValueError(f"attempt not found: {attempt_id}")

        attempt.attempt_status = AttemptStatus.ARTIFACT_COLLECTING.value
        attempt.result_ref = result_ref or attempt.result_ref
        attempt.manifest_artifact_id = manifest_artifact_id or attempt.manifest_artifact_id
        self.db.flush()
        return attempt

    def mark_completed(
        self,
        *,
        attempt_id: str,
        completion_status: str = "SUCCEEDED",
        finished_at: datetime | None = None,
        result_ref: str | None = None,
        manifest_artifact_id: str | None = None,
        runtime_ms: int | None = None,
        provider_runtime_ms: int | None = None,
        upload_ms: int | None = None,
    ) -> JobAttempt:
        attempt = self.get_attempt_by_attempt_id(attempt_id, for_update=True)
        if attempt is None:
            raise ValueError(f"attempt not found: {attempt_id}")

        attempt.attempt_status = AttemptStatus.COMPLETED.value
        attempt.completion_status = completion_status
        attempt.finished_at = finished_at or self.utcnow()
        attempt.result_ref = result_ref or attempt.result_ref
        attempt.manifest_artifact_id = manifest_artifact_id or attempt.manifest_artifact_id
        attempt.runtime_ms = runtime_ms if runtime_ms is not None else attempt.runtime_ms
        attempt.provider_runtime_ms = (
            provider_runtime_ms if provider_runtime_ms is not None else attempt.provider_runtime_ms
        )
        attempt.upload_ms = upload_ms if upload_ms is not None else attempt.upload_ms
        self.db.flush()
        return attempt

    def mark_failed(
        self,
        *,
        attempt_id: str,
        error_code: str | None = None,
        error_message: str | None = None,
        error_payload_json: dict | None = None,
        finished_at: datetime | None = None,
    ) -> JobAttempt:
        attempt = self.get_attempt_by_attempt_id(attempt_id, for_update=True)
        if attempt is None:
            raise ValueError(f"attempt not found: {attempt_id}")

        attempt.attempt_status = AttemptStatus.FAILED.value
        attempt.finished_at = finished_at or self.utcnow()
        attempt.error_code = error_code
        attempt.error_message = error_message
        attempt.error_payload_json = error_payload_json or attempt.error_payload_json or {}
        self.db.flush()
        return attempt

    def mark_stale(
        self,
        *,
        attempt_id: str,
        error_code: str = "ATTEMPT_STALE",
        error_message: str | None = None,
        error_payload_json: dict | None = None,
        finished_at: datetime | None = None,
    ) -> JobAttempt:
        attempt = self.get_attempt_by_attempt_id(attempt_id, for_update=True)
        if attempt is None:
            raise ValueError(f"attempt not found: {attempt_id}")

        attempt.attempt_status = AttemptStatus.STALE.value
        attempt.finished_at = finished_at or self.utcnow()
        attempt.error_code = error_code
        attempt.error_message = error_message
        attempt.error_payload_json = error_payload_json or attempt.error_payload_json or {}
        self.db.flush()
        return attempt

    def mark_timed_out(
        self,
        *,
        attempt_id: str,
        error_code: str = "ATTEMPT_TIMEOUT",
        error_message: str | None = None,
        finished_at: datetime | None = None,
    ) -> JobAttempt:
        attempt = self.get_attempt_by_attempt_id(attempt_id, for_update=True)
        if attempt is None:
            raise ValueError(f"attempt not found: {attempt_id}")

        attempt.attempt_status = AttemptStatus.TIMED_OUT.value
        attempt.finished_at = finished_at or self.utcnow()
        attempt.error_code = error_code
        attempt.error_message = error_message or attempt.error_message
        self.db.flush()
        return attempt

    @staticmethod
    def _assert_attempt_owner(
        *,
        attempt: JobAttempt,
        claim_token: str | None,
        worker_id: str | None,
    ) -> None:
        if claim_token is not None and attempt.claim_token != claim_token:
            raise ValueError(f"attempt {attempt.attempt_id} claim_token mismatch")
        if worker_id is not None and attempt.worker_id != worker_id:
            raise ValueError(f"attempt {attempt.attempt_id} worker_id mismatch")
