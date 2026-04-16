import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.enums.runtime import AttemptStatus, AttemptType, JobStatus, JobType, LeaseStatus
from app.enums.worker import WorkerHealthStatus
from app.models.job_attempt import JobAttempt
from app.models.runtime_job import RuntimeJob
from app.models.worker_lease import WorkerLease
from app.models.worker_registry import WorkerRegistry
from app.schemas.runtime import CompleteJobRequest, FailJobRequest
from app.services.runtime_complete_service import RuntimeCompleteService
from app.services.runtime_fail_service import RuntimeFailService


UTC = timezone.utc


def _resolve_database_url() -> str:
    return (
        os.getenv("RUNTIME_TERMINAL_TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or settings.database_url.replace("@postgres:", "@127.0.0.1:")
    )


class RuntimeTerminalRepositoryTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(_resolve_database_url(), future=True)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False, future=True)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        try:
            self.db.rollback()
            self.db.execute(delete(WorkerLease))
            self.db.execute(delete(JobAttempt))
            self.db.execute(delete(RuntimeJob))
            self.db.execute(delete(WorkerRegistry))
            self.db.commit()
        finally:
            self.db.close()

    def test_complete_job_marks_terminal_rows_and_preserves_existing_refs_on_none(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="complete-success",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
            worker_current_job_count=1,
            attempt_result_ref="minio://runtime/original-result.json",
            attempt_manifest_artifact_id="manifest-existing-1",
        )
        old_last_seen_at = seeded["worker"].last_seen_at

        request = CompleteJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            completion_status=JobStatus.SUCCEEDED.value,
            terminal_reason="done",
            result_ref=None,
            manifest_artifact_id=None,
            runtime_ms=1234,
            provider_runtime_ms=1111,
            upload_ms=123,
            metadata_json={"trace_id": "trace-complete"},
        )

        result = RuntimeCompleteService(self.db).complete_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.metadata_json, {"trace_id": "trace-complete"})
        self.assertIsNotNone(result.finished_at)

        self.assertEqual(job.job_status, JobStatus.SUCCEEDED.value)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNone(job.lease_expires_at)

        self.assertEqual(attempt.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(attempt.completion_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(attempt.result_ref, "minio://runtime/original-result.json")
        self.assertEqual(attempt.manifest_artifact_id, "manifest-existing-1")
        self.assertEqual(attempt.runtime_ms, 1234)
        self.assertEqual(attempt.provider_runtime_ms, 1111)
        self.assertEqual(attempt.upload_ms, 123)
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.RELEASED.value)
        self.assertIsNotNone(lease.last_heartbeat_at)

        self.assertEqual(worker.current_job_count, 0)
        self.assertGreater(worker.last_seen_at, old_last_seen_at)

    def test_fail_job_failed_releases_lease_and_persists_empty_payload_not_none(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-failed",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
            worker_current_job_count=1,
            attempt_error_payload_json={},
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
            terminal_reason="provider failed",
            error_code="PROVIDER_ERROR",
            error_message="provider failed",
            metadata_json={"trace_id": "trace-failed"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.FAILED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertIsNotNone(result.finished_at)

        self.assertEqual(job.job_status, JobStatus.FAILED.value)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNone(job.lease_expires_at)

        self.assertEqual(attempt.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(attempt.error_code, "PROVIDER_ERROR")
        self.assertEqual(attempt.error_message, "provider failed")
        self.assertEqual(attempt.error_payload_json, {})
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_timeout_waiting_retry_preserves_job_finished_and_lease_expiry(self) -> None:
        original_finished_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
        original_lease_expires_at = datetime(2026, 4, 1, 12, 5, 0, tzinfo=UTC)
        seeded = self._seed_active_runtime_graph(
            suffix="fail-timeout",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
            worker_current_job_count=1,
            job_finished_at=original_finished_at,
            job_lease_expires_at=original_lease_expires_at,
            attempt_error_message="previous timeout detail",
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            error_code=None,
            error_message=None,
            metadata_json={"trace_id": "trace-timeout"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(result.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, original_finished_at)

        self.assertEqual(job.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(job.finished_at, original_finished_at)
        self.assertEqual(job.lease_expires_at, original_lease_expires_at)

        self.assertEqual(attempt.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(attempt.error_code, "ATTEMPT_TIMEOUT")
        self.assertEqual(attempt.error_message, "previous timeout detail")
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_stale_expires_lease_and_preserves_job_retry_fields(self) -> None:
        original_finished_at = datetime(2026, 4, 1, 13, 0, 0, tzinfo=UTC)
        original_job_lease_expires_at = datetime(2026, 4, 1, 13, 5, 0, tzinfo=UTC)
        seeded = self._seed_active_runtime_graph(
            suffix="fail-stale",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.CLAIMED.value,
            worker_current_job_count=1,
            job_finished_at=original_finished_at,
            job_lease_expires_at=original_job_lease_expires_at,
            attempt_error_payload_json={},
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            expire_lease=True,
            metadata_json={"trace_id": "trace-stale"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.STALE.value)
        self.assertEqual(result.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(result.lease_status, LeaseStatus.EXPIRED.value)
        self.assertEqual(result.finished_at, original_finished_at)

        self.assertEqual(job.job_status, JobStatus.STALE.value)
        self.assertEqual(job.finished_at, original_finished_at)
        self.assertEqual(job.lease_expires_at, original_job_lease_expires_at)

        self.assertEqual(attempt.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(attempt.error_code, "ATTEMPT_STALE")
        self.assertEqual(attempt.error_payload_json, {})
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.EXPIRED.value)
        self.assertIsNotNone(lease.lease_expires_at)
        self.assertNotEqual(lease.lease_expires_at, original_job_lease_expires_at)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_failed_can_expire_lease_while_clearing_job_lease_expiry(self) -> None:
        original_job_lease_expires_at = datetime(2026, 4, 1, 14, 5, 0, tzinfo=UTC)
        seeded = self._seed_active_runtime_graph(
            suffix="fail-failed-expire",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
            worker_current_job_count=1,
            job_lease_expires_at=original_job_lease_expires_at,
            attempt_error_payload_json={},
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
            error_code="PROVIDER_ABORTED",
            error_message="provider aborted after start",
            expire_lease=True,
            metadata_json={"trace_id": "trace-failed-expire"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.FAILED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(result.lease_status, LeaseStatus.EXPIRED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertIsNotNone(result.finished_at)

        self.assertEqual(job.job_status, JobStatus.FAILED.value)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNone(job.lease_expires_at)

        self.assertEqual(attempt.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(attempt.error_code, "PROVIDER_ABORTED")
        self.assertEqual(attempt.error_message, "provider aborted after start")
        self.assertEqual(attempt.error_payload_json, {})
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.EXPIRED.value)
        self.assertIsNotNone(lease.lease_expires_at)
        self.assertNotEqual(lease.lease_expires_at, original_job_lease_expires_at)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_waiting_retry_writes_terminal_reason_and_explicit_timeout_code(self) -> None:
        original_finished_at = datetime(2026, 4, 1, 15, 0, 0, tzinfo=UTC)
        original_job_lease_expires_at = datetime(2026, 4, 1, 15, 5, 0, tzinfo=UTC)
        seeded = self._seed_active_runtime_graph(
            suffix="fail-timeout-reason",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
            worker_current_job_count=1,
            job_finished_at=original_finished_at,
            job_lease_expires_at=original_job_lease_expires_at,
            attempt_error_message="old timeout detail",
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason="retry scheduled after provider timeout",
            error_code="PROVIDER_TIMEOUT",
            error_message="provider timed out after 30s",
            metadata_json={"trace_id": "trace-timeout-reason"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(result.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.finished_at, original_finished_at)

        self.assertEqual(job.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(job.finished_at, original_finished_at)
        self.assertEqual(job.lease_expires_at, original_job_lease_expires_at)
        self.assertEqual(job.terminal_reason_code, "PROVIDER_TIMEOUT")
        self.assertEqual(job.terminal_reason_message, "retry scheduled after provider timeout")

        self.assertEqual(attempt.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(attempt.error_code, "PROVIDER_TIMEOUT")
        self.assertEqual(attempt.error_message, "provider timed out after 30s")
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_stale_writes_explicit_terminal_reason_and_error_fields(self) -> None:
        original_finished_at = datetime(2026, 4, 1, 16, 0, 0, tzinfo=UTC)
        original_job_lease_expires_at = datetime(2026, 4, 1, 16, 5, 0, tzinfo=UTC)
        seeded = self._seed_active_runtime_graph(
            suffix="fail-stale-reason",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
            worker_current_job_count=1,
            job_finished_at=original_finished_at,
            job_lease_expires_at=original_job_lease_expires_at,
            attempt_error_message="old stale detail",
            attempt_error_payload_json={"prior": True},
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            terminal_reason="worker heartbeat expired during artifact collection",
            error_code="WORKER_HEARTBEAT_EXPIRED",
            error_message="worker heartbeat missing for 90s",
            error_payload_json={"heartbeat_gap_seconds": 90},
            expire_lease=True,
            metadata_json={"trace_id": "trace-stale-reason"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.STALE.value)
        self.assertEqual(result.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(result.lease_status, LeaseStatus.EXPIRED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.finished_at, original_finished_at)

        self.assertEqual(job.job_status, JobStatus.STALE.value)
        self.assertEqual(job.finished_at, original_finished_at)
        self.assertEqual(job.lease_expires_at, original_job_lease_expires_at)
        self.assertEqual(job.terminal_reason_code, "WORKER_HEARTBEAT_EXPIRED")
        self.assertEqual(job.terminal_reason_message, "worker heartbeat expired during artifact collection")

        self.assertEqual(attempt.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(attempt.error_code, "WORKER_HEARTBEAT_EXPIRED")
        self.assertEqual(attempt.error_message, "worker heartbeat missing for 90s")
        self.assertEqual(attempt.error_payload_json, {"heartbeat_gap_seconds": 90})
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.EXPIRED.value)
        self.assertIsNotNone(lease.lease_expires_at)
        self.assertNotEqual(lease.lease_expires_at, original_job_lease_expires_at)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_timed_out_without_error_message_preserves_existing_attempt_message(self) -> None:
        original_finished_at = datetime(2026, 4, 1, 17, 0, 0, tzinfo=UTC)
        original_job_lease_expires_at = datetime(2026, 4, 1, 17, 5, 0, tzinfo=UTC)
        seeded = self._seed_active_runtime_graph(
            suffix="fail-timeout-inherit-message",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
            worker_current_job_count=1,
            job_finished_at=original_finished_at,
            job_lease_expires_at=original_job_lease_expires_at,
            attempt_error_message="provider stalled before timeout classification",
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            error_code="PROVIDER_TIMEOUT",
            error_message=None,
            metadata_json={"trace_id": "trace-timeout-inherit-message"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(result.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.finished_at, original_finished_at)

        self.assertEqual(job.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(job.finished_at, original_finished_at)
        self.assertEqual(job.lease_expires_at, original_job_lease_expires_at)
        self.assertEqual(job.terminal_reason_code, "PROVIDER_TIMEOUT")
        self.assertIsNone(job.terminal_reason_message)

        self.assertEqual(attempt.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(attempt.error_code, "PROVIDER_TIMEOUT")
        self.assertEqual(
            attempt.error_message,
            "provider stalled before timeout classification",
        )
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_failed_inherits_existing_payload_and_uses_error_message_as_terminal_reason(self) -> None:
        seeded = self._seed_active_runtime_graph(
            suffix="fail-failed-inherit-payload",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.STARTED.value,
            worker_current_job_count=1,
            attempt_error_payload_json={"provider_stage": "warmup", "retryable": False},
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
            error_code="PROVIDER_ABORTED",
            error_message="provider aborted before render kickoff",
            metadata_json={"trace_id": "trace-failed-inherit-payload"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.FAILED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertIsNotNone(result.finished_at)

        self.assertEqual(job.job_status, JobStatus.FAILED.value)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNone(job.lease_expires_at)
        self.assertEqual(job.terminal_reason_code, "PROVIDER_ABORTED")
        self.assertEqual(job.terminal_reason_message, "provider aborted before render kickoff")

        self.assertEqual(attempt.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(attempt.error_code, "PROVIDER_ABORTED")
        self.assertEqual(attempt.error_message, "provider aborted before render kickoff")
        self.assertEqual(attempt.error_payload_json, {"provider_stage": "warmup", "retryable": False})
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_timed_out_without_error_code_uses_job_status_as_terminal_reason_code(self) -> None:
        original_finished_at = datetime(2026, 4, 1, 18, 0, 0, tzinfo=UTC)
        original_job_lease_expires_at = datetime(2026, 4, 1, 18, 5, 0, tzinfo=UTC)
        seeded = self._seed_active_runtime_graph(
            suffix="fail-timeout-fallback-code",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
            worker_current_job_count=1,
            job_finished_at=original_finished_at,
            job_lease_expires_at=original_job_lease_expires_at,
            attempt_error_message="provider stalled before timeout classification",
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            error_code=None,
            error_message=None,
            terminal_reason=None,
            metadata_json={"trace_id": "trace-timeout-fallback-code"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(result.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.finished_at, original_finished_at)

        self.assertEqual(job.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(job.finished_at, original_finished_at)
        self.assertEqual(job.lease_expires_at, original_job_lease_expires_at)
        self.assertEqual(job.terminal_reason_code, JobStatus.WAITING_RETRY.value)
        self.assertIsNone(job.terminal_reason_message)

        self.assertEqual(attempt.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(attempt.error_code, "ATTEMPT_TIMEOUT")
        self.assertEqual(
            attempt.error_message,
            "provider stalled before timeout classification",
        )
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(worker.current_job_count, 0)

    def test_fail_job_stale_without_error_code_uses_job_status_as_terminal_reason_code_while_attempt_uses_attempt_stale_default(self) -> None:
        original_finished_at = datetime(2026, 4, 1, 19, 0, 0, tzinfo=UTC)
        original_job_lease_expires_at = datetime(2026, 4, 1, 19, 5, 0, tzinfo=UTC)
        seeded = self._seed_active_runtime_graph(
            suffix="fail-stale-fallback-code",
            job_status=JobStatus.RUNNING.value,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
            worker_current_job_count=1,
            job_finished_at=original_finished_at,
            job_lease_expires_at=original_job_lease_expires_at,
            attempt_error_message="worker became unreachable during artifact finalization",
            attempt_error_payload_json={"last_seen_step": "artifact_upload"},
        )

        request = FailJobRequest(
            job_id=seeded["job"].job_id,
            attempt_id=seeded["attempt"].attempt_id,
            worker_id=seeded["worker"].worker_id,
            claim_token=seeded["lease"].claim_token,
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            error_code=None,
            error_message=None,
            terminal_reason=None,
            metadata_json={"trace_id": "trace-stale-fallback-code"},
        )

        result = RuntimeFailService(self.db).fail_job(request)

        self.db.expire_all()
        job = self._get_job(seeded["job"].job_id)
        attempt = self._get_attempt(seeded["attempt"].attempt_id)
        lease = self._get_lease(seeded["lease"].claim_token)
        worker = self._get_worker(seeded["worker"].worker_id)

        self.assertEqual(result.job_status, JobStatus.STALE.value)
        self.assertEqual(result.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.finished_at, original_finished_at)

        self.assertEqual(job.job_status, JobStatus.STALE.value)
        self.assertEqual(job.finished_at, original_finished_at)
        self.assertEqual(job.lease_expires_at, original_job_lease_expires_at)
        self.assertEqual(job.terminal_reason_code, JobStatus.STALE.value)
        self.assertIsNone(job.terminal_reason_message)

        self.assertEqual(attempt.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(attempt.error_code, "ATTEMPT_STALE")
        self.assertIsNone(attempt.error_message)
        self.assertEqual(attempt.error_payload_json, {"last_seen_step": "artifact_upload"})
        self.assertIsNotNone(attempt.finished_at)

        self.assertEqual(lease.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(worker.current_job_count, 0)

    def _seed_active_runtime_graph(
        self,
        *,
        suffix: str,
        job_status: str,
        attempt_status: str,
        worker_current_job_count: int,
        attempt_result_ref: str | None = None,
        attempt_manifest_artifact_id: str | None = None,
        attempt_error_message: str | None = None,
        attempt_error_payload_json: dict | None = None,
        job_finished_at: datetime | None = None,
        job_lease_expires_at: datetime | None = None,
    ) -> dict[str, object]:
        base_time = datetime(2026, 4, 2, 12, 0, 0, tzinfo=UTC)
        started_at = base_time - timedelta(minutes=5)
        claimed_at = base_time - timedelta(minutes=4)
        worker_last_seen_at = base_time - timedelta(minutes=10)
        lease_expires_at = job_lease_expires_at or (base_time + timedelta(minutes=5))
        claim_token = f"claim-{suffix}-{uuid.uuid4().hex[:8]}"

        worker = WorkerRegistry(
            worker_id=f"worker-{suffix}-{uuid.uuid4().hex[:8]}",
            worker_type="runtime",
            hostname="localhost",
            health_status=WorkerHealthStatus.HEALTHY.value,
            current_job_count=worker_current_job_count,
            max_concurrency=2,
            started_at=base_time - timedelta(hours=1),
            last_seen_at=worker_last_seen_at,
            metadata_json={},
        )
        job = RuntimeJob(
            job_id=f"job-{suffix}-{uuid.uuid4().hex[:8]}",
            job_type=JobType.COMPILE.value,
            job_status=job_status,
            claimed_by_worker_id=worker.worker_id,
            active_claim_token=claim_token,
            claimed_at=claimed_at,
            started_at=started_at,
            finished_at=job_finished_at,
            lease_expires_at=lease_expires_at,
            metadata_json={},
        )
        attempt = JobAttempt(
            attempt_id=f"attempt-{suffix}-{uuid.uuid4().hex[:8]}",
            job_id=job.job_id,
            attempt_index=1,
            attempt_type=AttemptType.PRIMARY.value,
            attempt_status=attempt_status,
            worker_id=worker.worker_id,
            claim_token=claim_token,
            started_at=started_at,
            error_message=attempt_error_message,
            error_payload_json=attempt_error_payload_json or {},
            result_ref=attempt_result_ref,
            manifest_artifact_id=attempt_manifest_artifact_id,
            metadata_json={},
        )
        lease = WorkerLease(
            lease_id=f"lease-{suffix}-{uuid.uuid4().hex[:8]}",
            job_id=job.job_id,
            attempt_id=attempt.attempt_id,
            worker_id=worker.worker_id,
            claim_token=claim_token,
            lease_status=LeaseStatus.ACTIVE.value,
            lease_started_at=claimed_at,
            lease_expires_at=lease_expires_at,
            last_heartbeat_at=claimed_at,
            metadata_json={},
        )

        self.db.add(worker)
        self.db.add(job)
        self.db.flush()

        self.db.add(attempt)
        self.db.add(lease)
        self.db.commit()

        return {"worker": worker, "job": job, "attempt": attempt, "lease": lease}

    def _get_job(self, job_id: str) -> RuntimeJob:
        return self.db.execute(select(RuntimeJob).where(RuntimeJob.job_id == job_id)).scalar_one()

    def _get_attempt(self, attempt_id: str) -> JobAttempt:
        return self.db.execute(select(JobAttempt).where(JobAttempt.attempt_id == attempt_id)).scalar_one()

    def _get_lease(self, claim_token: str) -> WorkerLease:
        return self.db.execute(select(WorkerLease).where(WorkerLease.claim_token == claim_token)).scalar_one()

    def _get_worker(self, worker_id: str) -> WorkerRegistry:
        return self.db.execute(select(WorkerRegistry).where(WorkerRegistry.worker_id == worker_id)).scalar_one()


if __name__ == "__main__":
    unittest.main()
