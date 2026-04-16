from __future__ import annotations

import unittest
from contextlib import nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call
from uuid import UUID

from app.enums.runtime import AttemptStatus, JobStatus, LeaseStatus
from app.repositories.job_attempt_repository import JobAttemptRepository
from app.repositories.runtime_job_repository import RuntimeJobRepository
from app.schemas.runtime import CompleteJobRequest, FailJobRequest
from app.services.runtime_complete_service import RuntimeCompleteService
from app.services.runtime_errors import RuntimeLeaseConflictError, RuntimeStateConflictError
from app.services.runtime_fail_service import RuntimeFailService


class RuntimeTerminalWorkflowServiceTests(unittest.TestCase):
    def _build_db(self) -> MagicMock:
        db = MagicMock()
        db.begin.return_value = nullcontext()
        return db

    def test_complete_job_success_path(self) -> None:
        now = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
        manifest_artifact_id = UUID("12345678-1234-5678-1234-567812345678")
        request = CompleteJobRequest(
            job_id="job-1",
            attempt_id="attempt-1",
            worker_id="worker-1",
            claim_token="claim-1",
            completion_status=JobStatus.SUCCEEDED.value,
            terminal_reason="done",
            result_ref="minio://results/job-1.json",
            manifest_artifact_id=manifest_artifact_id,
            runtime_ms=101,
            provider_runtime_ms=88,
            upload_ms=13,
            metadata_json={"source": "unit-test"},
        )

        service = RuntimeCompleteService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-1",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-1",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=1)

        result = service.complete_job(request)

        service.job_attempts.mark_completed.assert_called_once_with(
            attempt_id=request.attempt_id,
            completion_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
            result_ref=request.result_ref,
            manifest_artifact_id=str(manifest_artifact_id),
            runtime_ms=101,
            provider_runtime_ms=88,
            upload_ms=13,
        )
        service.runtime_jobs.mark_succeeded.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            finished_at=now,
            terminal_reason_code=JobStatus.SUCCEEDED.value,
            terminal_reason_message="done",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.metadata_json, {"source": "unit-test"})
        self.assertEqual(result.current_job_count, 1)

    def test_complete_job_success_path_allows_none_manifest_artifact_id(self) -> None:
        now = datetime(2026, 4, 1, 12, 30, tzinfo=UTC)
        request = CompleteJobRequest(
            job_id="job-1-none-manifest",
            attempt_id="attempt-1-none-manifest",
            worker_id="worker-1-none-manifest",
            claim_token="claim-1-none-manifest",
            completion_status=JobStatus.SUCCEEDED.value,
            terminal_reason="done",
            result_ref="minio://results/job-1-none-manifest.json",
            manifest_artifact_id=None,
            runtime_ms=111,
            provider_runtime_ms=91,
            upload_ms=20,
            metadata_json={"source": "unit-test-none-manifest"},
        )

        service = RuntimeCompleteService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-1-none-manifest",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-1-none-manifest",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.complete_job(request)

        service.job_attempts.mark_completed.assert_called_once_with(
            attempt_id=request.attempt_id,
            completion_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
            result_ref=request.result_ref,
            manifest_artifact_id=None,
            runtime_ms=111,
            provider_runtime_ms=91,
            upload_ms=20,
        )
        service.runtime_jobs.mark_succeeded.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            finished_at=now,
            terminal_reason_code=JobStatus.SUCCEEDED.value,
            terminal_reason_message="done",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.metadata_json, {"source": "unit-test-none-manifest"})
        self.assertEqual(result.current_job_count, 0)

    def test_complete_job_success_path_allows_none_terminal_reason(self) -> None:
        now = datetime(2026, 4, 1, 12, 45, tzinfo=UTC)
        request = CompleteJobRequest(
            job_id="job-1-none-terminal-reason",
            attempt_id="attempt-1-none-terminal-reason",
            worker_id="worker-1-none-terminal-reason",
            claim_token="claim-1-none-terminal-reason",
            completion_status=JobStatus.SUCCEEDED.value,
            terminal_reason=None,
            result_ref="minio://results/job-1-none-terminal-reason.json",
            manifest_artifact_id="artifact-none-terminal-reason",
            runtime_ms=121,
            provider_runtime_ms=101,
            upload_ms=20,
            metadata_json={"source": "unit-test-none-terminal-reason"},
        )

        service = RuntimeCompleteService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-1-none-terminal-reason",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-1-none-terminal-reason",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.complete_job(request)

        service.job_attempts.mark_completed.assert_called_once_with(
            attempt_id=request.attempt_id,
            completion_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
            result_ref=request.result_ref,
            manifest_artifact_id="artifact-none-terminal-reason",
            runtime_ms=121,
            provider_runtime_ms=101,
            upload_ms=20,
        )
        service.runtime_jobs.mark_succeeded.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            finished_at=now,
            terminal_reason_code=JobStatus.SUCCEEDED.value,
            terminal_reason_message=None,
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.metadata_json, {"source": "unit-test-none-terminal-reason"})
        self.assertEqual(result.current_job_count, 0)

    def test_complete_job_success_path_defaults_completion_status_to_succeeded(self) -> None:
        now = datetime(2026, 4, 1, 12, 50, tzinfo=UTC)
        request = CompleteJobRequest(
            job_id="job-1-default-completion-status",
            attempt_id="attempt-1-default-completion-status",
            worker_id="worker-1-default-completion-status",
            claim_token="claim-1-default-completion-status",
            completion_status=None,
            terminal_reason="done-with-default-status",
            result_ref="minio://results/job-1-default-completion-status.json",
            manifest_artifact_id="artifact-default-completion-status",
            runtime_ms=131,
            provider_runtime_ms=109,
            upload_ms=22,
            metadata_json={"source": "unit-test-default-completion-status"},
        )

        service = RuntimeCompleteService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-1-default-completion-status",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-1-default-completion-status",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.complete_job(request)

        service.job_attempts.mark_completed.assert_called_once_with(
            attempt_id=request.attempt_id,
            completion_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
            result_ref=request.result_ref,
            manifest_artifact_id="artifact-default-completion-status",
            runtime_ms=131,
            provider_runtime_ms=109,
            upload_ms=22,
        )
        service.runtime_jobs.mark_succeeded.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            finished_at=now,
            terminal_reason_code=JobStatus.SUCCEEDED.value,
            terminal_reason_message="done-with-default-status",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.metadata_json, {"source": "unit-test-default-completion-status"})
        self.assertEqual(result.current_job_count, 0)

    def test_complete_job_success_path_allows_none_optional_telemetry(self) -> None:
        now = datetime(2026, 4, 1, 12, 55, tzinfo=UTC)
        request = CompleteJobRequest(
            job_id="job-1-none-optional-telemetry",
            attempt_id="attempt-1-none-optional-telemetry",
            worker_id="worker-1-none-optional-telemetry",
            claim_token="claim-1-none-optional-telemetry",
            completion_status=JobStatus.SUCCEEDED.value,
            terminal_reason="done-without-telemetry",
            result_ref=None,
            manifest_artifact_id="artifact-none-optional-telemetry",
            runtime_ms=None,
            provider_runtime_ms=None,
            upload_ms=None,
            metadata_json={"source": "unit-test-none-optional-telemetry"},
        )

        service = RuntimeCompleteService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-1-none-optional-telemetry",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-1-none-optional-telemetry",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.complete_job(request)

        service.job_attempts.mark_completed.assert_called_once_with(
            attempt_id=request.attempt_id,
            completion_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
            result_ref=None,
            manifest_artifact_id="artifact-none-optional-telemetry",
            runtime_ms=None,
            provider_runtime_ms=None,
            upload_ms=None,
        )
        service.runtime_jobs.mark_succeeded.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            finished_at=now,
            terminal_reason_code=JobStatus.SUCCEEDED.value,
            terminal_reason_message="done-without-telemetry",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.metadata_json, {"source": "unit-test-none-optional-telemetry"})
        self.assertEqual(result.current_job_count, 0)

    def test_fail_job_failed_releases_lease(self) -> None:
        now = datetime(2026, 4, 1, 13, 0, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-failed",
            attempt_id="attempt-failed",
            worker_id="worker-1",
            claim_token="claim-failed",
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
            terminal_reason="provider failed",
            error_code="PROVIDER_ERROR",
            error_message="provider error",
            error_payload_json={"provider": "veo"},
            expire_lease=False,
            metadata_json={"case": "failed-release"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-failed",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-failed",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.fail_job(request)

        service.job_attempts.mark_failed.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="PROVIDER_ERROR",
            error_message="provider error",
            error_payload_json={"provider": "veo"},
            finished_at=now,
        )
        service.job_attempts.mark_timed_out.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.FAILED.value,
            finished_at=now,
            terminal_reason_code="PROVIDER_ERROR",
            terminal_reason_message="provider failed",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.FAILED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.metadata_json, {"case": "failed-release"})

    def test_fail_job_failed_path_defaults_terminal_reason_code_to_next_job_status_when_error_code_none(self) -> None:
        now = datetime(2026, 4, 1, 13, 20, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-failed-default-error-code",
            attempt_id="attempt-failed-default-error-code",
            worker_id="worker-default-error-code",
            claim_token="claim-default-error-code",
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
            terminal_reason="provider failed without explicit code",
            error_code=None,
            error_message="provider error without code",
            error_payload_json={"provider": "veo", "case": "default-error-code"},
            expire_lease=False,
            metadata_json={"case": "failed-default-error-code"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-default-error-code",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-default-error-code",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.fail_job(request)

        service.job_attempts.mark_failed.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code=None,
            error_message="provider error without code",
            error_payload_json={"provider": "veo", "case": "default-error-code"},
            finished_at=now,
        )
        service.job_attempts.mark_timed_out.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.FAILED.value,
            finished_at=now,
            terminal_reason_code=JobStatus.FAILED.value,
            terminal_reason_message="provider failed without explicit code",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.FAILED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.metadata_json, {"case": "failed-default-error-code"})

    def test_fail_job_failed_path_defaults_terminal_reason_message_to_error_message_when_terminal_reason_none(self) -> None:
        now = datetime(2026, 4, 1, 13, 30, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-failed-default-terminal-reason",
            attempt_id="attempt-failed-default-terminal-reason",
            worker_id="worker-default-terminal-reason",
            claim_token="claim-default-terminal-reason",
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
            terminal_reason=None,
            error_code="PROVIDER_ERROR",
            error_message="provider error becomes terminal reason",
            error_payload_json={"provider": "veo", "case": "default-terminal-reason"},
            expire_lease=False,
            metadata_json={"case": "failed-default-terminal-reason"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-default-terminal-reason",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-default-terminal-reason",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.fail_job(request)

        service.job_attempts.mark_failed.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="PROVIDER_ERROR",
            error_message="provider error becomes terminal reason",
            error_payload_json={"provider": "veo", "case": "default-terminal-reason"},
            finished_at=now,
        )
        service.job_attempts.mark_timed_out.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.FAILED.value,
            finished_at=now,
            terminal_reason_code="PROVIDER_ERROR",
            terminal_reason_message="provider error becomes terminal reason",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.FAILED.value)
        self.assertEqual(result.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.metadata_json, {"case": "failed-default-terminal-reason"})

    def test_fail_job_timed_out_waiting_retry_expires_lease(self) -> None:
        now = datetime(2026, 4, 1, 14, 0, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-retry",
            attempt_id="attempt-timeout",
            worker_id="worker-2",
            claim_token="claim-timeout",
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason="heartbeat lost",
            error_code="ATTEMPT_TIMEOUT",
            error_message="timed out",
            expire_lease=True,
            metadata_json={"case": "timeout-expire"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-timeout",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_timed_out.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.TIMED_OUT.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.WAITING_RETRY.value,
            finished_at=None,
        )
        service.worker_leases.expire_lease.return_value = SimpleNamespace(
            lease_id="lease-timeout",
            lease_status=LeaseStatus.EXPIRED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=2)

        result = service.fail_job(request)

        service.job_attempts.mark_timed_out.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="ATTEMPT_TIMEOUT",
            error_message="timed out",
            finished_at=now,
        )
        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.WAITING_RETRY.value,
            finished_at=now,
            terminal_reason_code="ATTEMPT_TIMEOUT",
            terminal_reason_message="heartbeat lost",
        )
        service.worker_leases.expire_lease.assert_called_once_with(
            claim_token=request.claim_token,
            expired_at=now,
        )
        service.worker_leases.release_lease.assert_not_called()

        self.assertEqual(result.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(result.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(result.lease_status, LeaseStatus.EXPIRED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 2)

    def test_fail_job_timed_out_path_defaults_attempt_error_code_when_error_code_none(self) -> None:
        now = datetime(2026, 4, 1, 14, 20, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-timeout-default-error-code",
            attempt_id="attempt-timeout-default-error-code",
            worker_id="worker-timeout-default-error-code",
            claim_token="claim-timeout-default-error-code",
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason="heartbeat lost without explicit code",
            error_code=None,
            error_message="timed out without explicit code",
            expire_lease=True,
            metadata_json={"case": "timeout-default-error-code"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-timeout-default-error-code",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_timed_out.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.TIMED_OUT.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.WAITING_RETRY.value,
            finished_at=None,
        )
        service.worker_leases.expire_lease.return_value = SimpleNamespace(
            lease_id="lease-timeout-default-error-code",
            lease_status=LeaseStatus.EXPIRED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=1)

        result = service.fail_job(request)

        service.job_attempts.mark_timed_out.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="ATTEMPT_TIMEOUT",
            error_message="timed out without explicit code",
            finished_at=now,
        )
        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.WAITING_RETRY.value,
            finished_at=now,
            terminal_reason_code=JobStatus.WAITING_RETRY.value,
            terminal_reason_message="heartbeat lost without explicit code",
        )
        service.worker_leases.expire_lease.assert_called_once_with(
            claim_token=request.claim_token,
            expired_at=now,
        )
        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(result.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(result.lease_status, LeaseStatus.EXPIRED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 1)
        self.assertEqual(result.metadata_json, {"case": "timeout-default-error-code"})


    def test_fail_job_timed_out_path_defaults_terminal_reason_message_to_error_message_when_terminal_reason_none(self) -> None:
        now = datetime(2026, 4, 1, 14, 35, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-timeout-default-terminal-reason",
            attempt_id="attempt-timeout-default-terminal-reason",
            worker_id="worker-timeout-default-terminal-reason",
            claim_token="claim-timeout-default-terminal-reason",
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason=None,
            error_code="ATTEMPT_TIMEOUT",
            error_message="timeout error becomes terminal reason",
            expire_lease=True,
            metadata_json={"case": "timeout-default-terminal-reason"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-timeout-default-terminal-reason",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_timed_out.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.TIMED_OUT.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.WAITING_RETRY.value,
            finished_at=None,
        )
        service.worker_leases.expire_lease.return_value = SimpleNamespace(
            lease_id="lease-timeout-default-terminal-reason",
            lease_status=LeaseStatus.EXPIRED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.fail_job(request)

        service.job_attempts.mark_timed_out.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="ATTEMPT_TIMEOUT",
            error_message="timeout error becomes terminal reason",
            finished_at=now,
        )
        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.WAITING_RETRY.value,
            finished_at=now,
            terminal_reason_code="ATTEMPT_TIMEOUT",
            terminal_reason_message="timeout error becomes terminal reason",
        )
        service.worker_leases.expire_lease.assert_called_once_with(
            claim_token=request.claim_token,
            expired_at=now,
        )
        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(result.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(result.lease_status, LeaseStatus.EXPIRED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.metadata_json, {"case": "timeout-default-terminal-reason"})


    def test_fail_job_timed_out_path_defaults_error_code_and_terminal_reason_message_when_both_none(self) -> None:
        now = datetime(2026, 4, 1, 14, 50, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-timeout-default-both",
            attempt_id="attempt-timeout-default-both",
            worker_id="worker-timeout-default-both",
            claim_token="claim-timeout-default-both",
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason=None,
            error_code=None,
            error_message="timeout fallback message when both omitted",
            expire_lease=True,
            metadata_json={"case": "timeout-default-both"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-timeout-default-both",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_timed_out.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.TIMED_OUT.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.WAITING_RETRY.value,
            finished_at=None,
        )
        service.worker_leases.expire_lease.return_value = SimpleNamespace(
            lease_id="lease-timeout-default-both",
            lease_status=LeaseStatus.EXPIRED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=1)

        result = service.fail_job(request)

        service.job_attempts.mark_timed_out.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="ATTEMPT_TIMEOUT",
            error_message="timeout fallback message when both omitted",
            finished_at=now,
        )
        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.WAITING_RETRY.value,
            finished_at=now,
            terminal_reason_code=JobStatus.WAITING_RETRY.value,
            terminal_reason_message="timeout fallback message when both omitted",
        )
        service.worker_leases.expire_lease.assert_called_once_with(
            claim_token=request.claim_token,
            expired_at=now,
        )
        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(result.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(result.lease_status, LeaseStatus.EXPIRED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 1)
        self.assertEqual(result.metadata_json, {"case": "timeout-default-both"})


    def test_fail_job_stale_path_defaults_attempt_error_code_when_error_code_none(self) -> None:
        now = datetime(2026, 4, 1, 15, 20, tzinfo=UTC)
        payload = {"heartbeat_count": 9, "last_provider_state": "artifact_collecting"}
        request = FailJobRequest(
            job_id="job-stale-default-error-code",
            attempt_id="attempt-stale-default-error-code",
            worker_id="worker-stale-default-error-code",
            claim_token="claim-stale-default-error-code",
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            terminal_reason="attempt stale without explicit code",
            error_code=None,
            error_message="stale without explicit code",
            error_payload_json=payload,
            expire_lease=False,
            metadata_json={"case": "stale-default-error-code"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-stale-default-error-code",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_stale.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.STALE.value,
            finished_at=now,
            error_payload_json=payload,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.STALE.value,
            finished_at=None,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-stale-default-error-code",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=1)

        result = service.fail_job(request)

        service.job_attempts.mark_stale.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="ATTEMPT_STALE",
            error_message="stale without explicit code",
            error_payload_json=payload,
            finished_at=now,
        )
        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.STALE.value,
            finished_at=now,
            terminal_reason_code=JobStatus.STALE.value,
            terminal_reason_message="attempt stale without explicit code",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.STALE.value)
        self.assertEqual(result.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 1)
        self.assertEqual(result.metadata_json, {"case": "stale-default-error-code"})


    def test_fail_job_stale_path_defaults_terminal_reason_message_to_error_message_when_terminal_reason_none(self) -> None:
        now = datetime(2026, 4, 1, 15, 35, tzinfo=UTC)
        payload = {"heartbeat_count": 11, "last_provider_state": "provider_running", "case": "default-terminal-reason"}
        request = FailJobRequest(
            job_id="job-stale-default-terminal-reason",
            attempt_id="attempt-stale-default-terminal-reason",
            worker_id="worker-stale-default-terminal-reason",
            claim_token="claim-stale-default-terminal-reason",
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            terminal_reason=None,
            error_code="ATTEMPT_STALE",
            error_message="stale error becomes terminal reason",
            error_payload_json=payload,
            expire_lease=False,
            metadata_json={"case": "stale-default-terminal-reason"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-stale-default-terminal-reason",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_stale.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.STALE.value,
            finished_at=now,
            error_payload_json=payload,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.STALE.value,
            finished_at=None,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-stale-default-terminal-reason",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.fail_job(request)

        service.job_attempts.mark_stale.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="ATTEMPT_STALE",
            error_message="stale error becomes terminal reason",
            error_payload_json=payload,
            finished_at=now,
        )
        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.STALE.value,
            finished_at=now,
            terminal_reason_code="ATTEMPT_STALE",
            terminal_reason_message="stale error becomes terminal reason",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)
        service.worker_registry.mark_seen.assert_called_once_with(request.worker_id, seen_at=now)

        self.assertEqual(result.job_status, JobStatus.STALE.value)
        self.assertEqual(result.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.current_job_count, 0)
        self.assertEqual(result.metadata_json, {"case": "stale-default-terminal-reason"})


    def test_fail_job_stale_marks_attempt_stale_and_releases_lease(self) -> None:
        now = datetime(2026, 4, 1, 15, 0, tzinfo=UTC)
        payload = {"heartbeat_count": 7, "last_provider_state": "running"}
        request = FailJobRequest(
            job_id="job-stale",
            attempt_id="attempt-stale",
            worker_id="worker-3",
            claim_token="claim-stale",
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            error_message="attempt became stale",
            error_payload_json=payload,
            expire_lease=False,
            metadata_json={"case": "stale-release"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-stale",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_stale.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.STALE.value,
            finished_at=now,
            error_payload_json=payload,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.STALE.value,
            finished_at=None,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-stale",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        result = service.fail_job(request)

        service.job_attempts.mark_stale.assert_called_once_with(
            attempt_id=request.attempt_id,
            error_code="ATTEMPT_STALE",
            error_message="attempt became stale",
            error_payload_json=payload,
            finished_at=now,
        )
        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.runtime_jobs.mark_failed.assert_called_once_with(
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            next_status=JobStatus.STALE.value,
            finished_at=now,
            terminal_reason_code=JobStatus.STALE.value,
            terminal_reason_message="attempt became stale",
        )
        service.worker_leases.release_lease.assert_called_once_with(
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            released_at=now,
        )
        service.worker_leases.expire_lease.assert_not_called()

        self.assertEqual(result.job_status, JobStatus.STALE.value)
        self.assertEqual(result.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(result.lease_status, LeaseStatus.RELEASED.value)
        self.assertEqual(result.finished_at, now)
        self.assertEqual(result.metadata_json, {"case": "stale-release"})

    def test_complete_job_success_path_orders_terminal_writes_before_mark_seen(self) -> None:
        now = datetime(2026, 4, 1, 15, 20, tzinfo=UTC)
        request = CompleteJobRequest(
            job_id="job-complete-order",
            attempt_id="attempt-complete-order",
            worker_id="worker-complete-order",
            claim_token="claim-complete-order",
            completion_status=JobStatus.SUCCEEDED.value,
            terminal_reason="ordered complete",
            result_ref="minio://results/job-complete-order.json",
            metadata_json={"case": "complete-order"},
        )

        service = RuntimeCompleteService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-complete-order",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-complete-order",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        ordered_calls = MagicMock()
        ordered_calls.attach_mock(service.job_attempts.mark_completed, "mark_completed")
        ordered_calls.attach_mock(service.runtime_jobs.mark_succeeded, "mark_succeeded")
        ordered_calls.attach_mock(service.worker_leases.release_lease, "release_lease")
        ordered_calls.attach_mock(service.worker_registry.decrement_current_job_count, "decrement_current_job_count")
        ordered_calls.attach_mock(service.worker_registry.mark_seen, "mark_seen")

        service.complete_job(request)

        ordered_calls.assert_has_calls(
            [
                call.mark_completed(
                    attempt_id=request.attempt_id,
                    completion_status=JobStatus.SUCCEEDED.value,
                    finished_at=now,
                    result_ref=request.result_ref,
                    manifest_artifact_id=None,
                    runtime_ms=None,
                    provider_runtime_ms=None,
                    upload_ms=None,
                ),
                call.mark_succeeded(
                    job_id=request.job_id,
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    finished_at=now,
                    terminal_reason_code=JobStatus.SUCCEEDED.value,
                    terminal_reason_message="ordered complete",
                ),
                call.release_lease(
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    released_at=now,
                ),
                call.decrement_current_job_count(request.worker_id),
                call.mark_seen(request.worker_id, seen_at=now),
            ]
        )

    def test_fail_job_success_path_orders_expire_and_registry_updates_before_mark_seen(self) -> None:
        now = datetime(2026, 4, 1, 15, 30, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-fail-order",
            attempt_id="attempt-fail-order",
            worker_id="worker-fail-order",
            claim_token="claim-fail-order",
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason="ordered fail",
            error_code="ATTEMPT_TIMEOUT",
            error_message="ordered timeout",
            expire_lease=True,
            metadata_json={"case": "fail-order"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-fail-order",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_timed_out.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.TIMED_OUT.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.WAITING_RETRY.value,
            finished_at=None,
        )
        service.worker_leases.expire_lease.return_value = SimpleNamespace(
            lease_id="lease-fail-order",
            lease_status=LeaseStatus.EXPIRED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=1)

        ordered_calls = MagicMock()
        ordered_calls.attach_mock(service.job_attempts.mark_timed_out, "mark_timed_out")
        ordered_calls.attach_mock(service.runtime_jobs.mark_failed, "mark_failed")
        ordered_calls.attach_mock(service.worker_leases.expire_lease, "expire_lease")
        ordered_calls.attach_mock(service.worker_registry.decrement_current_job_count, "decrement_current_job_count")
        ordered_calls.attach_mock(service.worker_registry.mark_seen, "mark_seen")

        service.fail_job(request)

        ordered_calls.assert_has_calls(
            [
                call.mark_timed_out(
                    attempt_id=request.attempt_id,
                    error_code="ATTEMPT_TIMEOUT",
                    error_message="ordered timeout",
                    finished_at=now,
                ),
                call.mark_failed(
                    job_id=request.job_id,
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    next_status=JobStatus.WAITING_RETRY.value,
                    finished_at=now,
                    terminal_reason_code="ATTEMPT_TIMEOUT",
                    terminal_reason_message="ordered fail",
                ),
                call.expire_lease(
                    claim_token=request.claim_token,
                    expired_at=now,
                ),
                call.decrement_current_job_count(request.worker_id),
                call.mark_seen(request.worker_id, seen_at=now),
            ]
        )

    def test_fail_job_success_path_orders_release_and_registry_updates_before_mark_seen(self) -> None:
        now = datetime(2026, 4, 1, 15, 40, tzinfo=UTC)
        request = FailJobRequest(
            job_id="job-fail-release-order",
            attempt_id="attempt-fail-release-order",
            worker_id="worker-fail-release-order",
            claim_token="claim-fail-release-order",
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
            terminal_reason="ordered failed",
            error_code="PROVIDER_ERROR",
            error_message="ordered provider failure",
            expire_lease=False,
            metadata_json={"case": "fail-release-order"},
        )

        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()

        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id="lease-fail-release-order",
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id="lease-fail-release-order",
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(current_job_count=0)

        ordered_calls = MagicMock()
        ordered_calls.attach_mock(service.job_attempts.mark_failed, "mark_failed_attempt")
        ordered_calls.attach_mock(service.runtime_jobs.mark_failed, "mark_failed_job")
        ordered_calls.attach_mock(service.worker_leases.release_lease, "release_lease")
        ordered_calls.attach_mock(service.worker_registry.decrement_current_job_count, "decrement_current_job_count")
        ordered_calls.attach_mock(service.worker_registry.mark_seen, "mark_seen")

        service.fail_job(request)

        ordered_calls.assert_has_calls(
            [
                call.mark_failed_attempt(
                    attempt_id=request.attempt_id,
                    error_code="PROVIDER_ERROR",
                    error_message="ordered provider failure",
                    error_payload_json={},
                    finished_at=now,
                ),
                call.mark_failed_job(
                    job_id=request.job_id,
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    next_status=JobStatus.FAILED.value,
                    finished_at=now,
                    terminal_reason_code="PROVIDER_ERROR",
                    terminal_reason_message="ordered failed",
                ),
                call.release_lease(
                    claim_token=request.claim_token,
                    worker_id=request.worker_id,
                    released_at=now,
                ),
                call.decrement_current_job_count(request.worker_id),
                call.mark_seen(request.worker_id, seen_at=now),
            ]
        )


class RuntimeTerminalWorkflowConflictTests(unittest.TestCase):
    def _build_db(self) -> MagicMock:
        db = MagicMock()
        db.begin.return_value = nullcontext()
        return db

    def _build_complete_service(self) -> RuntimeCompleteService:
        service = RuntimeCompleteService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()
        return service

    def _build_fail_service(self) -> RuntimeFailService:
        service = RuntimeFailService(self._build_db())
        service.runtime_jobs = MagicMock()
        service.job_attempts = MagicMock()
        service.worker_leases = MagicMock()
        service.worker_registry = MagicMock()
        return service

    def _base_complete_request(self) -> CompleteJobRequest:
        return CompleteJobRequest(
            job_id='job-conflict',
            attempt_id='attempt-conflict',
            worker_id='worker-conflict',
            claim_token='claim-conflict',
            terminal_reason='done',
        )

    def _base_fail_request(self) -> FailJobRequest:
        return FailJobRequest(
            job_id='job-fail-conflict',
            attempt_id='attempt-fail-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-conflict',
            next_job_status=JobStatus.FAILED.value,
            attempt_terminal_status=AttemptStatus.FAILED.value,
            terminal_reason='failed',
            error_code='PROVIDER_ERROR',
            error_message='provider failed',
        )

    def test_complete_job_raises_lease_conflict_when_active_lease_missing(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 0, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = None

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'active lease not found for claim_token=claim-conflict',
        ):
            service.complete_job(request)

        service.runtime_jobs.get_by_job_id.assert_not_called()
        service.job_attempts.get_attempt_by_attempt_id.assert_not_called()

    def test_complete_job_raises_state_conflict_when_attempt_status_not_active(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 5, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.COMPLETED.value,
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'attempt attempt-conflict cannot complete from COMPLETED',
        ):
            service.complete_job(request)

        service.job_attempts.mark_completed.assert_not_called()
        service.runtime_jobs.mark_succeeded.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()

    def test_complete_job_maps_release_lease_value_error_to_lease_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 10, tzinfo=UTC)
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.side_effect = ValueError('lease lease-conflict worker_id mismatch')

        with self.assertRaisesRegex(RuntimeLeaseConflictError, 'lease lease-conflict worker_id mismatch'):
            service.complete_job(request)

        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_active_lease_not_found_value_error_to_lease_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 11, tzinfo=UTC)
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.side_effect = ValueError(
            'active lease not found for claim_token=claim-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'active lease not found for claim_token=claim-conflict',
        ):
            service.complete_job(request)

        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_active_lease_not_found_value_error_with_colon_to_lease_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 11, tzinfo=UTC)
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.side_effect = ValueError(
            'active lease not found for claim_token: claim-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'active lease not found for claim_token: claim-conflict',
        ):
            service.complete_job(request)

        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_decrement_current_job_count_value_error_to_state_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 12, tzinfo=UTC)
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.side_effect = ValueError(
            'worker not found: worker-complete-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'worker not found: worker-complete-conflict',
        ):
            service.complete_job(request)

        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_mark_seen_value_error_to_state_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 13, tzinfo=UTC)
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(
            worker_id=request.worker_id,
            current_job_count=0,
        )
        service.worker_registry.mark_seen.side_effect = ValueError(
            'worker not found: worker-complete-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'worker not found: worker-complete-conflict',
        ):
            service.complete_job(request)

        service.worker_registry.decrement_current_job_count.assert_called_once_with(request.worker_id)

    def test_fail_job_raises_lease_conflict_when_active_lease_missing(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 15, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = None

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'active lease not found for claim_token=claim-fail-conflict',
        ):
            service.fail_job(request)

        service.runtime_jobs.get_by_job_id.assert_not_called()
        service.job_attempts.get_attempt_by_attempt_id.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()

    def test_fail_job_raises_state_conflict_when_job_already_terminal(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 15, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'job job-fail-conflict already terminal: FAILED',
        ):
            service.fail_job(request)

        service.job_attempts.get_attempt_by_attempt_id.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()

    def test_fail_job_maps_release_lease_value_error_to_lease_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 20, tzinfo=UTC)
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.side_effect = ValueError(
            'lease lease-fail-conflict worker_id mismatch'
        )

        with self.assertRaisesRegex(RuntimeLeaseConflictError, 'lease lease-fail-conflict worker_id mismatch'):
            service.fail_job(request)

        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_release_lease_active_lease_not_found_value_error_to_lease_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 21, tzinfo=UTC)
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.side_effect = ValueError(
            'active lease not found for claim_token=claim-fail-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'active lease not found for claim_token=claim-fail-conflict',
        ):
            service.fail_job(request)

        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_release_lease_active_lease_not_found_value_error_with_colon_to_lease_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 21, tzinfo=UTC)
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.side_effect = ValueError(
            'active lease not found for claim_token: claim-fail-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'active lease not found for claim_token: claim-fail-conflict',
        ):
            service.fail_job(request)

        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_expire_lease_value_error_to_lease_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 22, tzinfo=UTC)
        request = self._base_fail_request().model_copy(update={'expire_lease': True})
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-expire-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.expire_lease.side_effect = ValueError(
            'active lease not found for claim_token: claim-fail-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'active lease not found for claim_token: claim-fail-conflict',
        ):
            service.fail_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_expire_lease_value_error_with_equals_to_lease_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 22, tzinfo=UTC)
        request = self._base_fail_request().model_copy(update={'expire_lease': True})
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-expire-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.expire_lease.side_effect = ValueError(
            'active lease not found for claim_token=claim-fail-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'active lease not found for claim_token=claim-fail-conflict',
        ):
            service.fail_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_decrement_current_job_count_value_error_to_state_conflict_after_expire_lease(self) -> None:
        now = datetime(2026, 4, 1, 18, 24, tzinfo=UTC)
        request = self._base_fail_request().model_copy(update={'expire_lease': True})
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-expire-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.expire_lease.return_value = SimpleNamespace(
            lease_id='lease-fail-expire-conflict',
            lease_status=LeaseStatus.EXPIRED.value,
        )
        service.worker_registry.decrement_current_job_count.side_effect = ValueError(
            'worker not found: worker-fail-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'worker not found: worker-fail-conflict',
        ):
            service.fail_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_seen_value_error_to_state_conflict_after_expire_lease(self) -> None:
        now = datetime(2026, 4, 1, 18, 25, tzinfo=UTC)
        request = self._base_fail_request().model_copy(update={'expire_lease': True})
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-expire-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.expire_lease.return_value = SimpleNamespace(
            lease_id='lease-fail-expire-conflict',
            lease_status=LeaseStatus.EXPIRED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(
            worker_id=request.worker_id,
            current_job_count=0,
        )
        service.worker_registry.mark_seen.side_effect = ValueError(
            'worker not found: worker-fail-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'worker not found: worker-fail-conflict',
        ):
            service.fail_job(request)

        service.worker_leases.release_lease.assert_not_called()

    def test_fail_job_maps_attempt_repository_value_error_to_state_conflict(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 25, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_failed.side_effect = ValueError('attempt not found: attempt-fail-conflict')

        with self.assertRaisesRegex(RuntimeStateConflictError, 'attempt not found: attempt-fail-conflict'):
            service.fail_job(request)

        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()

    def test_fail_job_maps_decrement_current_job_count_value_error_to_state_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 26, tzinfo=UTC)
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.side_effect = ValueError(
            'worker not found: worker-fail-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'worker not found: worker-fail-conflict',
        ):
            service.fail_job(request)

        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_seen_value_error_to_state_conflict(self) -> None:
        now = datetime(2026, 4, 1, 18, 27, tzinfo=UTC)
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.FAILED.value,
            finished_at=now,
        )
        service.worker_leases.release_lease.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            lease_status=LeaseStatus.RELEASED.value,
        )
        service.worker_registry.decrement_current_job_count.return_value = SimpleNamespace(
            worker_id=request.worker_id,
            current_job_count=0,
        )
        service.worker_registry.mark_seen.side_effect = ValueError(
            'worker not found: worker-fail-conflict'
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'worker not found: worker-fail-conflict',
        ):
            service.fail_job(request)

        service.worker_leases.expire_lease.assert_not_called()

    def test_complete_job_maps_mark_completed_value_error_to_state_conflict(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 27, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.side_effect = ValueError('attempt not found: attempt-conflict')

        with self.assertRaisesRegex(RuntimeStateConflictError, 'attempt not found: attempt-conflict'):
            service.complete_job(request)

        service.runtime_jobs.mark_succeeded.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_runtime_jobs_mark_succeeded_value_error_to_state_conflict(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        now = datetime(2026, 4, 1, 18, 28, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-complete-state-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.side_effect = ValueError('unexpected repository state')

        with self.assertRaisesRegex(RuntimeStateConflictError, 'unexpected repository state'):
            service.complete_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_timed_out_value_error_to_state_conflict(self) -> None:
        request = FailJobRequest(
            job_id='job-fail-timeout-conflict',
            attempt_id='attempt-timeout-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-timeout-conflict',
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason='timed out',
            error_code='ATTEMPT_TIMEOUT',
            error_message='provider timed out',
        )
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 28, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-timeout-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_timed_out.side_effect = ValueError(
            'attempt not found: attempt-timeout-conflict'
        )

        with self.assertRaisesRegex(RuntimeStateConflictError, 'attempt not found: attempt-timeout-conflict'):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_stale_value_error_to_state_conflict(self) -> None:
        request = FailJobRequest(
            job_id='job-fail-stale-conflict',
            attempt_id='attempt-stale-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-stale-conflict',
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            terminal_reason='stale',
            error_code='ATTEMPT_STALE',
            error_message='attempt stale',
            error_payload_json={'reason': 'heartbeat_lost'},
        )
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 29, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-stale-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_stale.side_effect = ValueError(
            'attempt not found: attempt-stale-conflict'
        )

        with self.assertRaisesRegex(RuntimeStateConflictError, 'attempt not found: attempt-stale-conflict'):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_mark_completed_worker_id_mismatch_to_lease_conflict(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 30, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.side_effect = ValueError(
            'attempt attempt-conflict worker_id mismatch'
        )

        with self.assertRaisesRegex(RuntimeLeaseConflictError, 'attempt attempt-conflict worker_id mismatch'):
            service.complete_job(request)

        service.runtime_jobs.mark_succeeded.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_mark_completed_claim_token_mismatch_to_lease_conflict(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 30, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-complete-attempt-claim-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.side_effect = ValueError(
            'attempt attempt-conflict claim_token mismatch'
        )

        with self.assertRaisesRegex(RuntimeLeaseConflictError, 'attempt attempt-conflict claim_token mismatch'):
            service.complete_job(request)

        service.runtime_jobs.mark_succeeded.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_mark_completed_attempt_job_id_mismatch_to_lease_conflict(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 30, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-complete-attempt-job-id-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.side_effect = ValueError('attempt.job_id mismatch')

        with self.assertRaisesRegex(RuntimeLeaseConflictError, r'attempt\.job_id mismatch'):
            service.complete_job(request)

        service.runtime_jobs.mark_succeeded.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_runtime_jobs_mark_succeeded_claim_token_mismatch_to_lease_conflict(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        now = datetime(2026, 4, 1, 18, 31, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-complete-claim-token-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.side_effect = ValueError(
            'job job-complete claim_token mismatch'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'job job-complete claim_token mismatch',
        ):
            service.complete_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_runtime_jobs_mark_succeeded_claimed_by_worker_id_mismatch_to_lease_conflict(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        now = datetime(2026, 4, 1, 18, 32, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-complete-worker-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.side_effect = ValueError(
            'job job-complete claimed_by_worker_id mismatch'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'job job-complete claimed_by_worker_id mismatch',
        ):
            service.complete_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_maps_runtime_jobs_mark_succeeded_worker_id_mismatch_to_lease_conflict(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        now = datetime(2026, 4, 1, 18, 33, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-complete-worker-id-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
        )
        service.job_attempts.mark_completed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.COMPLETED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_succeeded.side_effect = ValueError(
            'job job-complete worker_id mismatch'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'job job-complete worker_id mismatch',
        ):
            service.complete_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_timed_out_worker_id_mismatch_to_lease_conflict(self) -> None:
        request = FailJobRequest(
            job_id='job-fail-timeout-conflict',
            attempt_id='attempt-timeout-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-timeout-conflict',
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason='timed out',
            error_code='ATTEMPT_TIMEOUT',
            error_message='provider timed out',
        )
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 31, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-timeout-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.STARTED.value,
        )
        service.job_attempts.mark_timed_out.side_effect = ValueError(
            'attempt attempt-timeout-conflict worker_id mismatch'
        )

        with self.assertRaisesRegex(RuntimeLeaseConflictError, 'attempt attempt-timeout-conflict worker_id mismatch'):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_timed_out_claim_token_mismatch_to_lease_conflict(self) -> None:
        request = FailJobRequest(
            job_id='job-fail-timeout-claim-conflict',
            attempt_id='attempt-timeout-claim-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-timeout-claim-conflict',
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason='timed out',
            error_code='ATTEMPT_TIMEOUT',
            error_message='provider timed out',
        )
        service = self._build_fail_service()
        now = datetime(2026, 4, 1, 18, 34, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-timeout-claim-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_timed_out.side_effect = ValueError(
            'attempt attempt-timeout-claim-conflict claim_token mismatch'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'attempt attempt-timeout-claim-conflict claim_token mismatch',
        ):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_timed_out_attempt_job_id_mismatch_to_lease_conflict(self) -> None:
        request = FailJobRequest(
            job_id='job-fail-timeout-attempt-job-id-conflict',
            attempt_id='attempt-timeout-attempt-job-id-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-timeout-attempt-job-id-conflict',
            next_job_status=JobStatus.WAITING_RETRY.value,
            attempt_terminal_status=AttemptStatus.TIMED_OUT.value,
            terminal_reason='timed out',
            error_code='ATTEMPT_TIMEOUT',
            error_message='provider timed out',
        )
        service = self._build_fail_service()
        now = datetime(2026, 4, 1, 18, 34, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-timeout-attempt-job-id-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
        )
        service.job_attempts.mark_timed_out.side_effect = ValueError('attempt.job_id mismatch')

        with self.assertRaisesRegex(RuntimeLeaseConflictError, r'attempt\.job_id mismatch'):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_stale_worker_id_mismatch_to_lease_conflict(self) -> None:
        request = FailJobRequest(
            job_id='job-fail-stale-conflict',
            attempt_id='attempt-stale-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-stale-conflict',
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            terminal_reason='stale',
            error_code='ATTEMPT_STALE',
            error_message='attempt stale',
            error_payload_json={'reason': 'heartbeat_lost'},
        )
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 32, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-stale-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_stale.side_effect = ValueError(
            'attempt attempt-stale-conflict worker_id mismatch'
        )

        with self.assertRaisesRegex(RuntimeLeaseConflictError, 'attempt attempt-stale-conflict worker_id mismatch'):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_stale_claim_token_mismatch_to_lease_conflict(self) -> None:
        request = FailJobRequest(
            job_id='job-fail-stale-claim-conflict',
            attempt_id='attempt-stale-claim-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-stale-claim-conflict',
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            terminal_reason='stale',
            error_code='ATTEMPT_STALE',
            error_message='attempt stale',
            error_payload_json={'reason': 'heartbeat_lost'},
        )
        service = self._build_fail_service()
        now = datetime(2026, 4, 1, 18, 35, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-stale-claim-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_stale.side_effect = ValueError(
            'attempt attempt-stale-claim-conflict claim_token mismatch'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'attempt attempt-stale-claim-conflict claim_token mismatch',
        ):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_stale_attempt_job_id_mismatch_to_lease_conflict(self) -> None:
        request = FailJobRequest(
            job_id='job-fail-stale-attempt-job-id-conflict',
            attempt_id='attempt-stale-attempt-job-id-conflict',
            worker_id='worker-fail-conflict',
            claim_token='claim-fail-stale-attempt-job-id-conflict',
            next_job_status=JobStatus.STALE.value,
            attempt_terminal_status=AttemptStatus.STALE.value,
            terminal_reason='stale',
            error_code='ATTEMPT_STALE',
            error_message='attempt stale',
            error_payload_json={'reason': 'heartbeat_lost'},
        )
        service = self._build_fail_service()
        now = datetime(2026, 4, 1, 18, 35, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-stale-attempt-job-id-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_stale.side_effect = ValueError('attempt.job_id mismatch')

        with self.assertRaisesRegex(RuntimeLeaseConflictError, r'attempt\.job_id mismatch'):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_failed_worker_id_mismatch_to_lease_conflict(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 33, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_failed.side_effect = ValueError(
            'attempt attempt-fail-conflict worker_id mismatch'
        )

        with self.assertRaisesRegex(RuntimeLeaseConflictError, 'attempt attempt-fail-conflict worker_id mismatch'):
            service.fail_job(request)

        service.job_attempts.mark_timed_out.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_failed_claim_token_mismatch_to_lease_conflict(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 33, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_failed.side_effect = ValueError(
            'attempt attempt-fail-conflict claim_token mismatch'
        )

        with self.assertRaisesRegex(RuntimeLeaseConflictError, 'attempt attempt-fail-conflict claim_token mismatch'):
            service.fail_job(request)

        service.job_attempts.mark_timed_out.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_mark_failed_attempt_job_id_mismatch_to_lease_conflict(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 18, 33, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-attempt-job-id-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_failed.side_effect = ValueError('attempt.job_id mismatch')

        with self.assertRaisesRegex(RuntimeLeaseConflictError, r'attempt\.job_id mismatch'):
            service.fail_job(request)

        service.job_attempts.mark_timed_out.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_runtime_jobs_mark_failed_claimed_by_worker_id_mismatch_to_lease_conflict(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        now = datetime(2026, 4, 1, 18, 34, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.side_effect = ValueError(
            'job job-fail-conflict claimed_by_worker_id mismatch'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'job job-fail-conflict claimed_by_worker_id mismatch',
        ):
            service.fail_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_runtime_jobs_mark_failed_claim_token_mismatch_to_lease_conflict(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        now = datetime(2026, 4, 1, 18, 36, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-claim-token-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.side_effect = ValueError(
            'job job-fail-conflict claim_token mismatch'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'job job-fail-conflict claim_token mismatch',
        ):
            service.fail_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_runtime_jobs_mark_failed_worker_id_mismatch_to_lease_conflict(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        now = datetime(2026, 4, 1, 18, 37, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-worker-id-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.side_effect = ValueError(
            'job job-fail-conflict worker_id mismatch'
        )

        with self.assertRaisesRegex(
            RuntimeLeaseConflictError,
            'job job-fail-conflict worker_id mismatch',
        ):
            service.fail_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_fail_job_maps_runtime_jobs_mark_failed_value_error_to_state_conflict(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        now = datetime(2026, 4, 1, 18, 38, tzinfo=UTC)
        service.runtime_jobs.utcnow.return_value = now
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-state-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.CLAIMED.value,
        )
        service.job_attempts.mark_failed.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            attempt_status=AttemptStatus.FAILED.value,
            finished_at=now,
        )
        service.runtime_jobs.mark_failed.side_effect = ValueError('unexpected repository state')

        with self.assertRaisesRegex(RuntimeStateConflictError, 'unexpected repository state'):
            service.fail_job(request)

        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()
        service.worker_registry.decrement_current_job_count.assert_not_called()
        service.worker_registry.mark_seen.assert_not_called()

    def test_complete_job_raises_lease_conflict_for_lease_identity_mismatches(self) -> None:
        now = datetime(2026, 4, 1, 18, 30, tzinfo=UTC)
        variants = [
            ({'job_id': 'job-other'}, 'lease.job_id mismatch'),
            ({'worker_id': 'worker-other'}, 'lease.worker_id mismatch'),
            ({'attempt_id': 'attempt-other'}, 'lease.attempt_id mismatch'),
        ]

        for lease_override, expected_message in variants:
            with self.subTest(expected_message=expected_message):
                request = self._base_complete_request()
                service = self._build_complete_service()
                service.runtime_jobs.utcnow.return_value = now
                service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
                    lease_id='lease-conflict',
                    job_id=lease_override.get('job_id', request.job_id),
                    worker_id=lease_override.get('worker_id', request.worker_id),
                    attempt_id=lease_override.get('attempt_id', request.attempt_id),
                    lease_status=LeaseStatus.ACTIVE.value,
                )

                with self.assertRaisesRegex(RuntimeLeaseConflictError, expected_message):
                    service.complete_job(request)

                service.runtime_jobs.get_by_job_id.assert_not_called()
                service.job_attempts.get_attempt_by_attempt_id.assert_not_called()

    def test_complete_job_raises_lease_conflict_for_job_claim_mismatches(self) -> None:
        now = datetime(2026, 4, 1, 18, 35, tzinfo=UTC)
        variants = [
            ({'active_claim_token': 'claim-other'}, 'job.active_claim_token mismatch'),
            ({'claimed_by_worker_id': 'worker-other'}, 'job.claimed_by_worker_id mismatch'),
        ]

        for job_override, expected_message in variants:
            with self.subTest(expected_message=expected_message):
                request = self._base_complete_request()
                service = self._build_complete_service()
                service.runtime_jobs.utcnow.return_value = now
                service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
                    lease_id='lease-conflict',
                    job_id=request.job_id,
                    worker_id=request.worker_id,
                    attempt_id=request.attempt_id,
                    lease_status=LeaseStatus.ACTIVE.value,
                )
                service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
                    job_id=request.job_id,
                    job_status=JobStatus.RUNNING.value,
                    active_claim_token=job_override.get('active_claim_token', request.claim_token),
                    claimed_by_worker_id=job_override.get('claimed_by_worker_id', request.worker_id),
                )

                with self.assertRaisesRegex(RuntimeLeaseConflictError, expected_message):
                    service.complete_job(request)

                service.job_attempts.get_attempt_by_attempt_id.assert_not_called()
                service.runtime_jobs.mark_succeeded.assert_not_called()

    def test_complete_job_raises_lease_conflict_for_attempt_identity_mismatches(self) -> None:
        now = datetime(2026, 4, 1, 18, 40, tzinfo=UTC)
        variants = [
            ({'job_id': 'job-other'}, 'attempt.job_id mismatch'),
            ({'claim_token': 'claim-other'}, 'attempt.claim_token mismatch'),
            ({'worker_id': 'worker-other'}, 'attempt.worker_id mismatch'),
        ]

        for attempt_override, expected_message in variants:
            with self.subTest(expected_message=expected_message):
                request = self._base_complete_request()
                service = self._build_complete_service()
                service.runtime_jobs.utcnow.return_value = now
                service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
                    lease_id='lease-conflict',
                    job_id=request.job_id,
                    worker_id=request.worker_id,
                    attempt_id=request.attempt_id,
                    lease_status=LeaseStatus.ACTIVE.value,
                )
                service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
                    job_id=request.job_id,
                    job_status=JobStatus.RUNNING.value,
                    active_claim_token=request.claim_token,
                    claimed_by_worker_id=request.worker_id,
                )
                service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
                    attempt_id=request.attempt_id,
                    job_id=attempt_override.get('job_id', request.job_id),
                    claim_token=attempt_override.get('claim_token', request.claim_token),
                    worker_id=attempt_override.get('worker_id', request.worker_id),
                    attempt_status=AttemptStatus.STARTED.value,
                )

                with self.assertRaisesRegex(RuntimeLeaseConflictError, expected_message):
                    service.complete_job(request)

                service.job_attempts.mark_completed.assert_not_called()
                service.runtime_jobs.mark_succeeded.assert_not_called()
                service.worker_leases.release_lease.assert_not_called()

    def test_fail_job_raises_lease_conflict_for_lease_identity_mismatches(self) -> None:
        now = datetime(2026, 4, 1, 18, 45, tzinfo=UTC)
        variants = [
            ({'job_id': 'job-other'}, 'lease.job_id mismatch'),
            ({'worker_id': 'worker-other'}, 'lease.worker_id mismatch'),
            ({'attempt_id': 'attempt-other'}, 'lease.attempt_id mismatch'),
        ]

        for lease_override, expected_message in variants:
            with self.subTest(expected_message=expected_message):
                request = self._base_fail_request()
                service = self._build_fail_service()
                service.runtime_jobs.utcnow.return_value = now
                service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
                    lease_id='lease-fail-conflict',
                    job_id=lease_override.get('job_id', request.job_id),
                    worker_id=lease_override.get('worker_id', request.worker_id),
                    attempt_id=lease_override.get('attempt_id', request.attempt_id),
                    lease_status=LeaseStatus.ACTIVE.value,
                )

                with self.assertRaisesRegex(RuntimeLeaseConflictError, expected_message):
                    service.fail_job(request)

                service.runtime_jobs.get_by_job_id.assert_not_called()
                service.job_attempts.get_attempt_by_attempt_id.assert_not_called()

    def test_fail_job_raises_lease_conflict_for_job_claim_mismatches(self) -> None:
        now = datetime(2026, 4, 1, 18, 50, tzinfo=UTC)
        variants = [
            ({'active_claim_token': 'claim-other'}, 'job.active_claim_token mismatch'),
            ({'claimed_by_worker_id': 'worker-other'}, 'job.claimed_by_worker_id mismatch'),
        ]

        for job_override, expected_message in variants:
            with self.subTest(expected_message=expected_message):
                request = self._base_fail_request()
                service = self._build_fail_service()
                service.runtime_jobs.utcnow.return_value = now
                service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
                    lease_id='lease-fail-conflict',
                    job_id=request.job_id,
                    worker_id=request.worker_id,
                    attempt_id=request.attempt_id,
                    lease_status=LeaseStatus.ACTIVE.value,
                )
                service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
                    job_id=request.job_id,
                    job_status=JobStatus.RUNNING.value,
                    active_claim_token=job_override.get('active_claim_token', request.claim_token),
                    claimed_by_worker_id=job_override.get('claimed_by_worker_id', request.worker_id),
                )

                with self.assertRaisesRegex(RuntimeLeaseConflictError, expected_message):
                    service.fail_job(request)

                service.job_attempts.get_attempt_by_attempt_id.assert_not_called()
                service.runtime_jobs.mark_failed.assert_not_called()

    def test_fail_job_raises_lease_conflict_for_attempt_identity_mismatches(self) -> None:
        now = datetime(2026, 4, 1, 18, 55, tzinfo=UTC)
        variants = [
            ({'job_id': 'job-other'}, 'attempt.job_id mismatch'),
            ({'claim_token': 'claim-other'}, 'attempt.claim_token mismatch'),
            ({'worker_id': 'worker-other'}, 'attempt.worker_id mismatch'),
        ]

        for attempt_override, expected_message in variants:
            with self.subTest(expected_message=expected_message):
                request = self._base_fail_request()
                service = self._build_fail_service()
                service.runtime_jobs.utcnow.return_value = now
                service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
                    lease_id='lease-fail-conflict',
                    job_id=request.job_id,
                    worker_id=request.worker_id,
                    attempt_id=request.attempt_id,
                    lease_status=LeaseStatus.ACTIVE.value,
                )
                service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
                    job_id=request.job_id,
                    job_status=JobStatus.RUNNING.value,
                    active_claim_token=request.claim_token,
                    claimed_by_worker_id=request.worker_id,
                )
                service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
                    attempt_id=request.attempt_id,
                    job_id=attempt_override.get('job_id', request.job_id),
                    claim_token=attempt_override.get('claim_token', request.claim_token),
                    worker_id=attempt_override.get('worker_id', request.worker_id),
                    attempt_status=AttemptStatus.CLAIMED.value,
                )

                with self.assertRaisesRegex(RuntimeLeaseConflictError, expected_message):
                    service.fail_job(request)

                service.job_attempts.mark_failed.assert_not_called()
                service.runtime_jobs.mark_failed.assert_not_called()
                service.worker_leases.release_lease.assert_not_called()
                service.worker_leases.expire_lease.assert_not_called()

    def test_complete_job_raises_state_conflict_when_job_not_found(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 19, 15, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = None

        with self.assertRaisesRegex(RuntimeStateConflictError, 'job not found: job-conflict'):
            service.complete_job(request)

        service.job_attempts.get_attempt_by_attempt_id.assert_not_called()
        service.job_attempts.mark_completed.assert_not_called()
        service.runtime_jobs.mark_succeeded.assert_not_called()

    def test_complete_job_raises_state_conflict_when_job_already_terminal(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 19, 20, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.SUCCEEDED.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'job job-conflict already terminal: SUCCEEDED',
        ):
            service.complete_job(request)

        service.job_attempts.get_attempt_by_attempt_id.assert_not_called()
        service.job_attempts.mark_completed.assert_not_called()
        service.runtime_jobs.mark_succeeded.assert_not_called()

    def test_complete_job_raises_state_conflict_when_attempt_not_found(self) -> None:
        request = self._base_complete_request()
        service = self._build_complete_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 19, 25, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = None

        with self.assertRaisesRegex(RuntimeStateConflictError, 'attempt not found: attempt-conflict'):
            service.complete_job(request)

        service.job_attempts.mark_completed.assert_not_called()
        service.runtime_jobs.mark_succeeded.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()

    def test_fail_job_raises_state_conflict_when_job_not_found(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 19, 30, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = None

        with self.assertRaisesRegex(RuntimeStateConflictError, 'job not found: job-fail-conflict'):
            service.fail_job(request)

        service.job_attempts.get_attempt_by_attempt_id.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()

    def test_fail_job_raises_state_conflict_when_attempt_not_found(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 19, 35, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = None

        with self.assertRaisesRegex(RuntimeStateConflictError, 'attempt not found: attempt-fail-conflict'):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()

    def test_fail_job_raises_state_conflict_when_attempt_status_not_active(self) -> None:
        request = self._base_fail_request()
        service = self._build_fail_service()
        service.runtime_jobs.utcnow.return_value = datetime(2026, 4, 1, 19, 40, tzinfo=UTC)
        service.worker_leases.get_active_lease_by_claim_token.return_value = SimpleNamespace(
            lease_id='lease-fail-conflict',
            job_id=request.job_id,
            worker_id=request.worker_id,
            attempt_id=request.attempt_id,
            lease_status=LeaseStatus.ACTIVE.value,
        )
        service.runtime_jobs.get_by_job_id.return_value = SimpleNamespace(
            job_id=request.job_id,
            job_status=JobStatus.RUNNING.value,
            active_claim_token=request.claim_token,
            claimed_by_worker_id=request.worker_id,
        )
        service.job_attempts.get_attempt_by_attempt_id.return_value = SimpleNamespace(
            attempt_id=request.attempt_id,
            job_id=request.job_id,
            claim_token=request.claim_token,
            worker_id=request.worker_id,
            attempt_status=AttemptStatus.COMPLETED.value,
        )

        with self.assertRaisesRegex(
            RuntimeStateConflictError,
            'attempt attempt-fail-conflict cannot fail from COMPLETED',
        ):
            service.fail_job(request)

        service.job_attempts.mark_failed.assert_not_called()
        service.job_attempts.mark_timed_out.assert_not_called()
        service.job_attempts.mark_stale.assert_not_called()
        service.runtime_jobs.mark_failed.assert_not_called()
        service.worker_leases.release_lease.assert_not_called()
        service.worker_leases.expire_lease.assert_not_called()


class RuntimeRepositoryValueErrorMappingTests(unittest.TestCase):
    def test_complete_service_maps_repository_value_errors_by_message_boundary(self) -> None:
        cases = [
            ('active lease not found for claim_token: claim-1', RuntimeLeaseConflictError),
            ('lease lease-1 worker_id mismatch', RuntimeLeaseConflictError),
            ('job job-1 claim_token mismatch', RuntimeLeaseConflictError),
            ('job job-1 claimed_by_worker_id mismatch', RuntimeLeaseConflictError),
            ('lease.job_id mismatch', RuntimeLeaseConflictError),
            ('lease.worker_id mismatch', RuntimeLeaseConflictError),
            ('lease.attempt_id mismatch', RuntimeLeaseConflictError),
            ('attempt.job_id mismatch', RuntimeLeaseConflictError),
            ('attempt.claim_token mismatch', RuntimeLeaseConflictError),
            ('attempt.worker_id mismatch', RuntimeLeaseConflictError),
            ('job not found: job-1', RuntimeStateConflictError),
            ('attempt not found: attempt-1', RuntimeStateConflictError),
            ('unexpected repository state', RuntimeStateConflictError),
        ]

        for message, expected_type in cases:
            with self.subTest(message=message):
                mapped = RuntimeCompleteService._map_repository_value_error(ValueError(message))
                self.assertIsInstance(mapped, expected_type)
                self.assertEqual(str(mapped), message)

    def test_fail_service_maps_repository_value_errors_by_message_boundary(self) -> None:
        cases = [
            ('active lease not found for claim_token: claim-1', RuntimeLeaseConflictError),
            ('lease lease-1 worker_id mismatch', RuntimeLeaseConflictError),
            ('job job-1 claim_token mismatch', RuntimeLeaseConflictError),
            ('job job-1 claimed_by_worker_id mismatch', RuntimeLeaseConflictError),
            ('lease.job_id mismatch', RuntimeLeaseConflictError),
            ('lease.worker_id mismatch', RuntimeLeaseConflictError),
            ('lease.attempt_id mismatch', RuntimeLeaseConflictError),
            ('attempt.job_id mismatch', RuntimeLeaseConflictError),
            ('attempt.claim_token mismatch', RuntimeLeaseConflictError),
            ('attempt.worker_id mismatch', RuntimeLeaseConflictError),
            ('job not found: job-1', RuntimeStateConflictError),
            ('attempt not found: attempt-1', RuntimeStateConflictError),
            ('unexpected repository state', RuntimeStateConflictError),
        ]

        for message, expected_type in cases:
            with self.subTest(message=message):
                mapped = RuntimeFailService._map_repository_value_error(ValueError(message))
                self.assertIsInstance(mapped, expected_type)
                self.assertEqual(str(mapped), message)


class RuntimeJobRepositoryMarkSucceededTests(unittest.TestCase):
    def test_mark_succeeded_sets_terminal_fields_and_clears_lease(self) -> None:
        now = datetime(2026, 4, 1, 18, 50, tzinfo=UTC)
        existing_lease_expires_at = datetime(2026, 4, 1, 20, 30, tzinfo=UTC)
        db = MagicMock()
        repo = RuntimeJobRepository(db)
        job = SimpleNamespace(
            job_id='job-succeeded-semantics',
            job_status=JobStatus.RUNNING.value,
            active_claim_token='claim-succeeded-semantics',
            claimed_by_worker_id='worker-succeeded-semantics',
            finished_at=None,
            lease_expires_at=existing_lease_expires_at,
            terminal_reason_code=None,
            terminal_reason_message=None,
        )
        repo.get_by_job_id = MagicMock(return_value=job)

        result = repo.mark_succeeded(
            job_id='job-succeeded-semantics',
            claim_token='claim-succeeded-semantics',
            worker_id='worker-succeeded-semantics',
            finished_at=now,
            terminal_reason_code='JOB_COMPLETED',
            terminal_reason_message='manifest finalized',
        )

        self.assertIs(result, job)
        self.assertEqual(job.job_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(job.finished_at, now)
        self.assertIsNone(job.lease_expires_at)
        self.assertEqual(job.terminal_reason_code, 'JOB_COMPLETED')
        self.assertEqual(job.terminal_reason_message, 'manifest finalized')
        db.flush.assert_called_once_with()

    def test_mark_succeeded_uses_repo_utcnow_when_finished_at_missing(self) -> None:
        now = datetime(2026, 4, 1, 18, 55, tzinfo=UTC)
        previous_finished_at = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
        db = MagicMock()
        repo = RuntimeJobRepository(db)
        repo.utcnow = MagicMock(return_value=now)
        job = SimpleNamespace(
            job_id='job-succeeded-utcnow',
            job_status=JobStatus.RUNNING.value,
            active_claim_token='claim-succeeded-utcnow',
            claimed_by_worker_id='worker-succeeded-utcnow',
            finished_at=previous_finished_at,
            lease_expires_at=datetime(2026, 4, 1, 21, 0, tzinfo=UTC),
            terminal_reason_code='OLD_CODE',
            terminal_reason_message='old message',
        )
        repo.get_by_job_id = MagicMock(return_value=job)

        repo.mark_succeeded(
            job_id='job-succeeded-utcnow',
            claim_token='claim-succeeded-utcnow',
            worker_id='worker-succeeded-utcnow',
            finished_at=None,
            terminal_reason_code=None,
            terminal_reason_message=None,
        )

        self.assertEqual(job.job_status, JobStatus.SUCCEEDED.value)
        self.assertEqual(job.finished_at, now)
        self.assertIsNone(job.lease_expires_at)
        self.assertIsNone(job.terminal_reason_code)
        self.assertIsNone(job.terminal_reason_message)
        repo.utcnow.assert_called_once_with()
        db.flush.assert_called_once_with()


class RuntimeJobRepositoryMarkFailedTests(unittest.TestCase):
    def test_mark_failed_sets_finished_at_and_clears_lease_for_failed(self) -> None:
        now = datetime(2026, 4, 1, 19, 0, tzinfo=UTC)
        existing_finished_at = datetime(2026, 4, 1, 10, 0, tzinfo=UTC)
        existing_lease_expires_at = datetime(2026, 4, 1, 20, 0, tzinfo=UTC)
        db = MagicMock()
        repo = RuntimeJobRepository(db)
        job = SimpleNamespace(
            job_id='job-failed-semantics',
            job_status=JobStatus.RUNNING.value,
            active_claim_token='claim-failed-semantics',
            claimed_by_worker_id='worker-failed-semantics',
            finished_at=existing_finished_at,
            lease_expires_at=existing_lease_expires_at,
            terminal_reason_code=None,
            terminal_reason_message=None,
        )
        repo.get_by_job_id = MagicMock(return_value=job)

        result = repo.mark_failed(
            job_id='job-failed-semantics',
            claim_token='claim-failed-semantics',
            worker_id='worker-failed-semantics',
            next_status=JobStatus.FAILED.value,
            finished_at=now,
            terminal_reason_code='PROVIDER_ERROR',
            terminal_reason_message='provider failed terminally',
        )

        self.assertIs(result, job)
        self.assertEqual(job.job_status, JobStatus.FAILED.value)
        self.assertEqual(job.finished_at, now)
        self.assertIsNone(job.lease_expires_at)
        self.assertEqual(job.terminal_reason_code, 'PROVIDER_ERROR')
        self.assertEqual(job.terminal_reason_message, 'provider failed terminally')
        db.flush.assert_called_once_with()

    def test_mark_failed_preserves_finished_at_and_lease_for_waiting_retry(self) -> None:
        now = datetime(2026, 4, 1, 19, 5, tzinfo=UTC)
        existing_finished_at = datetime(2026, 4, 1, 11, 0, tzinfo=UTC)
        existing_lease_expires_at = datetime(2026, 4, 1, 21, 0, tzinfo=UTC)
        db = MagicMock()
        repo = RuntimeJobRepository(db)
        job = SimpleNamespace(
            job_id='job-retry-semantics',
            job_status=JobStatus.RUNNING.value,
            active_claim_token='claim-retry-semantics',
            claimed_by_worker_id='worker-retry-semantics',
            finished_at=existing_finished_at,
            lease_expires_at=existing_lease_expires_at,
            terminal_reason_code=None,
            terminal_reason_message=None,
        )
        repo.get_by_job_id = MagicMock(return_value=job)

        result = repo.mark_failed(
            job_id='job-retry-semantics',
            claim_token='claim-retry-semantics',
            worker_id='worker-retry-semantics',
            next_status=JobStatus.WAITING_RETRY.value,
            finished_at=now,
            terminal_reason_code='ATTEMPT_TIMEOUT',
            terminal_reason_message='retry later',
        )

        self.assertIs(result, job)
        self.assertEqual(job.job_status, JobStatus.WAITING_RETRY.value)
        self.assertEqual(job.finished_at, existing_finished_at)
        self.assertEqual(job.lease_expires_at, existing_lease_expires_at)
        self.assertEqual(job.terminal_reason_code, 'ATTEMPT_TIMEOUT')
        self.assertEqual(job.terminal_reason_message, 'retry later')
        db.flush.assert_called_once_with()

    def test_mark_failed_preserves_finished_at_and_lease_for_stale(self) -> None:
        now = datetime(2026, 4, 1, 19, 10, tzinfo=UTC)
        existing_finished_at = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
        existing_lease_expires_at = datetime(2026, 4, 1, 22, 0, tzinfo=UTC)
        db = MagicMock()
        repo = RuntimeJobRepository(db)
        job = SimpleNamespace(
            job_id='job-stale-semantics',
            job_status=JobStatus.RUNNING.value,
            active_claim_token='claim-stale-semantics',
            claimed_by_worker_id='worker-stale-semantics',
            finished_at=existing_finished_at,
            lease_expires_at=existing_lease_expires_at,
            terminal_reason_code=None,
            terminal_reason_message=None,
        )
        repo.get_by_job_id = MagicMock(return_value=job)

        result = repo.mark_failed(
            job_id='job-stale-semantics',
            claim_token='claim-stale-semantics',
            worker_id='worker-stale-semantics',
            next_status=JobStatus.STALE.value,
            finished_at=now,
            terminal_reason_code='ATTEMPT_STALE',
            terminal_reason_message='lease stale',
        )

        self.assertIs(result, job)
        self.assertEqual(job.job_status, JobStatus.STALE.value)
        self.assertEqual(job.finished_at, existing_finished_at)
        self.assertEqual(job.lease_expires_at, existing_lease_expires_at)
        self.assertEqual(job.terminal_reason_code, 'ATTEMPT_STALE')
        self.assertEqual(job.terminal_reason_message, 'lease stale')
        db.flush.assert_called_once_with()


class JobAttemptRepositoryMarkCompletedTests(unittest.TestCase):
    def test_mark_completed_overwrites_terminal_fields_when_values_provided(self) -> None:
        finished_at = datetime(2026, 4, 1, 19, 15, tzinfo=UTC)
        db = MagicMock()
        repo = JobAttemptRepository(db)
        attempt = SimpleNamespace(
            attempt_id="attempt-completed-1",
            attempt_status=AttemptStatus.ARTIFACT_COLLECTING.value,
            completion_status=None,
            finished_at=None,
            result_ref="minio-result-old",
            manifest_artifact_id="artifact-old",
            runtime_ms=10,
            provider_runtime_ms=9,
            upload_ms=1,
        )
        repo.get_attempt_by_attempt_id = MagicMock(return_value=attempt)

        result = repo.mark_completed(
            attempt_id="attempt-completed-1",
            completion_status="SUCCEEDED",
            finished_at=finished_at,
            result_ref="minio-result-new",
            manifest_artifact_id="artifact-new",
            runtime_ms=210,
            provider_runtime_ms=180,
            upload_ms=30,
        )

        self.assertIs(result, attempt)
        self.assertEqual(attempt.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(attempt.completion_status, "SUCCEEDED")
        self.assertEqual(attempt.finished_at, finished_at)
        self.assertEqual(attempt.result_ref, "minio-result-new")
        self.assertEqual(attempt.manifest_artifact_id, "artifact-new")
        self.assertEqual(attempt.runtime_ms, 210)
        self.assertEqual(attempt.provider_runtime_ms, 180)
        self.assertEqual(attempt.upload_ms, 30)
        db.flush.assert_called_once_with()

    def test_mark_completed_preserves_existing_optional_fields_when_values_missing(self) -> None:
        now = datetime(2026, 4, 1, 19, 20, tzinfo=UTC)
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.utcnow = MagicMock(return_value=now)
        attempt = SimpleNamespace(
            attempt_id="attempt-completed-2",
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
            completion_status="OLD_STATUS",
            finished_at=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
            result_ref="existing-result-ref",
            manifest_artifact_id="artifact-existing",
            runtime_ms=310,
            provider_runtime_ms=280,
            upload_ms=30,
        )
        repo.get_attempt_by_attempt_id = MagicMock(return_value=attempt)

        repo.mark_completed(
            attempt_id="attempt-completed-2",
            completion_status="PARTIAL_SUCCESS",
            finished_at=None,
            result_ref=None,
            manifest_artifact_id=None,
            runtime_ms=None,
            provider_runtime_ms=None,
            upload_ms=None,
        )

        self.assertEqual(attempt.attempt_status, AttemptStatus.COMPLETED.value)
        self.assertEqual(attempt.completion_status, "PARTIAL_SUCCESS")
        self.assertEqual(attempt.finished_at, now)
        self.assertEqual(attempt.result_ref, "existing-result-ref")
        self.assertEqual(attempt.manifest_artifact_id, "artifact-existing")
        self.assertEqual(attempt.runtime_ms, 310)
        self.assertEqual(attempt.provider_runtime_ms, 280)
        self.assertEqual(attempt.upload_ms, 30)
        repo.utcnow.assert_called_once_with()
        db.flush.assert_called_once_with()

    def test_mark_completed_raises_value_error_when_attempt_missing(self) -> None:
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.get_attempt_by_attempt_id = MagicMock(return_value=None)

        with self.assertRaisesRegex(ValueError, "attempt not found: missing-attempt"):
            repo.mark_completed(attempt_id="missing-attempt")

        repo.get_attempt_by_attempt_id.assert_called_once_with("missing-attempt", for_update=True)
        db.flush.assert_not_called()


class JobAttemptRepositoryMarkFailedTests(unittest.TestCase):
    def test_mark_failed_overwrites_error_fields_and_payload_when_values_provided(self) -> None:
        finished_at = datetime(2026, 4, 1, 19, 25, tzinfo=UTC)
        db = MagicMock()
        repo = JobAttemptRepository(db)
        attempt = SimpleNamespace(
            attempt_id="attempt-failed-1",
            attempt_status=AttemptStatus.STARTED.value,
            finished_at=None,
            error_code="OLD_CODE",
            error_message="old message",
            error_payload_json={"existing": True},
        )
        repo.get_attempt_by_attempt_id = MagicMock(return_value=attempt)

        result = repo.mark_failed(
            attempt_id="attempt-failed-1",
            error_code="PROVIDER_ERROR",
            error_message="provider failed",
            error_payload_json={"provider_run_id": "run-456"},
            finished_at=finished_at,
        )

        self.assertIs(result, attempt)
        self.assertEqual(attempt.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(attempt.finished_at, finished_at)
        self.assertEqual(attempt.error_code, "PROVIDER_ERROR")
        self.assertEqual(attempt.error_message, "provider failed")
        self.assertEqual(attempt.error_payload_json, {"provider_run_id": "run-456"})
        db.flush.assert_called_once_with()

    def test_mark_failed_preserves_existing_payload_but_clears_code_and_message_when_missing(self) -> None:
        now = datetime(2026, 4, 1, 19, 30, tzinfo=UTC)
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.utcnow = MagicMock(return_value=now)
        attempt = SimpleNamespace(
            attempt_id="attempt-failed-2",
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
            finished_at=datetime(2026, 4, 1, 13, 0, tzinfo=UTC),
            error_code="OLD_CODE",
            error_message="old message",
            error_payload_json={"provider_run_id": "run-existing"},
        )
        repo.get_attempt_by_attempt_id = MagicMock(return_value=attempt)

        repo.mark_failed(
            attempt_id="attempt-failed-2",
            error_code=None,
            error_message=None,
            error_payload_json=None,
            finished_at=None,
        )

        self.assertEqual(attempt.attempt_status, AttemptStatus.FAILED.value)
        self.assertEqual(attempt.finished_at, now)
        self.assertIsNone(attempt.error_code)
        self.assertIsNone(attempt.error_message)
        self.assertEqual(attempt.error_payload_json, {"provider_run_id": "run-existing"})
        repo.utcnow.assert_called_once_with()
        db.flush.assert_called_once_with()

    def test_mark_failed_raises_value_error_when_attempt_missing(self) -> None:
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.get_attempt_by_attempt_id = MagicMock(return_value=None)

        with self.assertRaisesRegex(ValueError, "attempt not found: missing-attempt"):
            repo.mark_failed(attempt_id="missing-attempt")

        repo.get_attempt_by_attempt_id.assert_called_once_with("missing-attempt", for_update=True)
        db.flush.assert_not_called()


class JobAttemptRepositoryMarkTimedOutTests(unittest.TestCase):
    def test_mark_timed_out_overwrites_terminal_fields_when_values_provided(self) -> None:
        finished_at = datetime(2026, 4, 1, 19, 35, tzinfo=UTC)
        db = MagicMock()
        repo = JobAttemptRepository(db)
        attempt = SimpleNamespace(
            attempt_id="attempt-timeout-1",
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
            finished_at=None,
            error_code="OLD_TIMEOUT",
            error_message="old timeout message",
        )
        repo.get_attempt_by_attempt_id = MagicMock(return_value=attempt)

        result = repo.mark_timed_out(
            attempt_id="attempt-timeout-1",
            error_code="PROVIDER_TIMEOUT",
            error_message="provider timed out",
            finished_at=finished_at,
        )

        self.assertIs(result, attempt)
        self.assertEqual(attempt.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(attempt.finished_at, finished_at)
        self.assertEqual(attempt.error_code, "PROVIDER_TIMEOUT")
        self.assertEqual(attempt.error_message, "provider timed out")
        db.flush.assert_called_once_with()

    def test_mark_timed_out_preserves_existing_message_and_uses_default_code_when_missing(self) -> None:
        now = datetime(2026, 4, 1, 19, 40, tzinfo=UTC)
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.utcnow = MagicMock(return_value=now)
        attempt = SimpleNamespace(
            attempt_id="attempt-timeout-2",
            attempt_status=AttemptStatus.STARTED.value,
            finished_at=datetime(2026, 4, 1, 14, 0, tzinfo=UTC),
            error_code="OLD_TIMEOUT",
            error_message="keep this message",
        )
        repo.get_attempt_by_attempt_id = MagicMock(return_value=attempt)

        repo.mark_timed_out(
            attempt_id="attempt-timeout-2",
            error_message=None,
            finished_at=None,
        )

        self.assertEqual(attempt.attempt_status, AttemptStatus.TIMED_OUT.value)
        self.assertEqual(attempt.finished_at, now)
        self.assertEqual(attempt.error_code, "ATTEMPT_TIMEOUT")
        self.assertEqual(attempt.error_message, "keep this message")
        repo.utcnow.assert_called_once_with()
        db.flush.assert_called_once_with()

    def test_mark_timed_out_raises_value_error_when_attempt_missing(self) -> None:
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.get_attempt_by_attempt_id = MagicMock(return_value=None)

        with self.assertRaisesRegex(ValueError, "attempt not found: missing-attempt"):
            repo.mark_timed_out(attempt_id="missing-attempt")

        repo.get_attempt_by_attempt_id.assert_called_once_with("missing-attempt", for_update=True)
        db.flush.assert_not_called()


class JobAttemptRepositoryMarkStaleTests(unittest.TestCase):
    def test_mark_stale_sets_terminal_state_and_payload(self) -> None:
        now = datetime(2026, 4, 1, 16, 0, tzinfo=UTC)
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.utcnow = MagicMock(return_value=now)
        attempt = SimpleNamespace(
            attempt_id="attempt-1",
            attempt_status=AttemptStatus.STARTED.value,
            finished_at=None,
            error_code=None,
            error_message=None,
            error_payload_json={"existing": True},
        )
        repo.get_attempt_by_attempt_id = MagicMock(return_value=attempt)

        result = repo.mark_stale(
            attempt_id="attempt-1",
            error_code="ATTEMPT_STALE",
            error_message="lease expired",
            error_payload_json={"lease_status": LeaseStatus.EXPIRED.value},
        )

        self.assertIs(result, attempt)
        self.assertEqual(attempt.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(attempt.finished_at, now)
        self.assertEqual(attempt.error_code, "ATTEMPT_STALE")
        self.assertEqual(attempt.error_message, "lease expired")
        self.assertEqual(attempt.error_payload_json, {"lease_status": LeaseStatus.EXPIRED.value})
        db.flush.assert_called_once_with()

    def test_mark_stale_preserves_existing_payload_when_request_payload_missing(self) -> None:
        now = datetime(2026, 4, 1, 17, 0, tzinfo=UTC)
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.utcnow = MagicMock(return_value=now)
        attempt = SimpleNamespace(
            attempt_id="attempt-2",
            attempt_status=AttemptStatus.PROVIDER_RUNNING.value,
            finished_at=None,
            error_code=None,
            error_message=None,
            error_payload_json={"provider_run_id": "run-123"},
        )
        repo.get_attempt_by_attempt_id = MagicMock(return_value=attempt)

        repo.mark_stale(
            attempt_id="attempt-2",
            error_message="provider lease stale",
            error_payload_json=None,
        )

        self.assertEqual(attempt.attempt_status, AttemptStatus.STALE.value)
        self.assertEqual(attempt.finished_at, now)
        self.assertEqual(attempt.error_code, "ATTEMPT_STALE")
        self.assertEqual(attempt.error_message, "provider lease stale")
        self.assertEqual(attempt.error_payload_json, {"provider_run_id": "run-123"})
        db.flush.assert_called_once_with()

    def test_mark_stale_raises_value_error_when_attempt_missing(self) -> None:
        db = MagicMock()
        repo = JobAttemptRepository(db)
        repo.get_attempt_by_attempt_id = MagicMock(return_value=None)

        with self.assertRaisesRegex(ValueError, "attempt not found: missing-attempt"):
            repo.mark_stale(attempt_id="missing-attempt")

        repo.get_attempt_by_attempt_id.assert_called_once_with("missing-attempt", for_update=True)
        db.flush.assert_not_called()


if __name__ == "__main__":
    unittest.main()
