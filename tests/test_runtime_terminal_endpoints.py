import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.services.runtime_errors import RuntimeLeaseConflictError, RuntimeStateConflictError


class RuntimeTerminalEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_db] = lambda: iter([object()])
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def test_get_terminal_view_success_returns_contract(self) -> None:
        result = {
            "job_id": "job-1",
            "job_status": "RUNNING",
            "claimed_by_worker_id": "worker-1",
            "active_claim_token": "claim-1",
            "attempt_count": 1,
            "queued_at": "2026-04-02T11:50:00Z",
            "claimed_at": "2026-04-02T11:55:00Z",
            "started_at": "2026-04-02T11:56:00Z",
            "finished_at": None,
            "lease_expires_at": "2026-04-02T12:05:00Z",
            "terminal_reason_code": None,
            "terminal_reason_message": None,
            "metadata_json": {"trace_id": "trace-1"},
            "latest_attempt": {
                "attempt_id": "attempt-1",
                "attempt_status": "PROVIDER_RUNNING",
                "attempt_index": 1,
                "worker_id": "worker-1",
                "claim_token": "claim-1",
                "started_at": "2026-04-02T11:56:00Z",
                "finished_at": None,
                "completion_status": None,
                "error_code": None,
                "error_message": None,
                "error_payload_json": {},
                "result_ref": None,
                "manifest_artifact_id": None,
                "runtime_ms": None,
                "provider_runtime_ms": None,
                "upload_ms": None,
                "metrics_json": {"progress": 0.5},
                "metadata_json": {"attempt_trace": "trace-a"},
            },
            "active_lease": {
                "lease_id": "lease-1",
                "job_id": "job-1",
                "attempt_id": "attempt-1",
                "worker_id": "worker-1",
                "claim_token": "claim-1",
                "lease_status": "ACTIVE",
                "lease_started_at": "2026-04-02T11:55:00Z",
                "lease_expires_at": "2026-04-02T12:05:00Z",
                "last_heartbeat_at": "2026-04-02T12:00:00Z",
                "heartbeat_count": 3,
                "extension_count": 1,
                "revoked_at": None,
                "revoked_reason": None,
                "metadata_json": {"lease_trace": "trace-l"},
            },
        }

        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.get_terminal_view.return_value = result
            facade_cls.return_value = facade

            response = self.client.get("/api/v1/runtime/terminal/jobs/job-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), result)
        facade_cls.assert_called_once()
        facade.get_terminal_view.assert_called_once_with("job-1")

    def test_get_terminal_view_returns_404_when_job_missing(self) -> None:
        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.get_terminal_view.return_value = None
            facade_cls.return_value = facade

            response = self.client.get("/api/v1/runtime/terminal/jobs/job-missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "detail": "job not found: job-missing",
                "error_type": "runtime_job_not_found",
                "job_id": "job-missing",
                "attempt_id": None,
                "worker_id": None,
                "claim_token": None,
                "metadata_json": {},
            },
        )

    def test_complete_job_success_returns_contract(self) -> None:
        finished_at = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)
        payload = {
            "job_id": "job-1",
            "attempt_id": "attempt-1",
            "worker_id": "worker-1",
            "claim_token": "claim-1",
            "completion_status": "SUCCEEDED",
            "terminal_reason": "done",
            "result_ref": "minio://runtime/job-1/result.json",
            "manifest_artifact_id": "550e8400-e29b-41d4-a716-446655440000",
            "runtime_ms": 1000,
            "provider_runtime_ms": 900,
            "upload_ms": 100,
            "metadata_json": {"trace_id": "trace-1"},
        }
        result = {
            "job_id": "job-1",
            "attempt_id": "attempt-1",
            "lease_id": "lease-1",
            "job_status": "SUCCEEDED",
            "attempt_status": "COMPLETED",
            "lease_status": "RELEASED",
            "worker_id": "worker-1",
            "current_job_count": 0,
            "finished_at": finished_at,
            "metadata_json": {"trace_id": "trace-1"},
        }

        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.complete_job.return_value = result
            facade_cls.return_value = facade

            response = self.client.post("/api/v1/runtime/terminal/complete", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "job_id": "job-1",
                "attempt_id": "attempt-1",
                "lease_id": "lease-1",
                "job_status": "SUCCEEDED",
                "attempt_status": "COMPLETED",
                "lease_status": "RELEASED",
                "worker_id": "worker-1",
                "current_job_count": 0,
                "finished_at": "2026-04-02T12:00:00Z",
                "metadata_json": {"trace_id": "trace-1"},
            },
        )
        facade_cls.assert_called_once()
        request_model = facade.complete_job.call_args.args[0]
        self.assertEqual(request_model.job_id, payload["job_id"])
        self.assertEqual(str(request_model.manifest_artifact_id), payload["manifest_artifact_id"])
        self.assertEqual(request_model.metadata_json, payload["metadata_json"])

    def test_complete_job_maps_lease_conflict_to_409(self) -> None:
        payload = {
            "job_id": "job-1",
            "attempt_id": "attempt-1",
            "worker_id": "worker-1",
            "claim_token": "claim-1",
        }

        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.complete_job.side_effect = RuntimeLeaseConflictError("lease.worker_id mismatch")
            facade_cls.return_value = facade

            response = self.client.post("/api/v1/runtime/terminal/complete", json=payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {
                "detail": "lease.worker_id mismatch",
                "error_type": "runtime_lease_conflict",
                "job_id": "job-1",
                "attempt_id": "attempt-1",
                "worker_id": "worker-1",
                "claim_token": "claim-1",
                "metadata_json": {},
            },
        )

    def test_complete_job_maps_state_conflict_to_409(self) -> None:
        payload = {
            "job_id": "job-1",
            "attempt_id": "attempt-1",
            "worker_id": "worker-1",
            "claim_token": "claim-1",
        }

        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.complete_job.side_effect = RuntimeStateConflictError("job job-1 already terminal: SUCCEEDED")
            facade_cls.return_value = facade

            response = self.client.post("/api/v1/runtime/terminal/complete", json=payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {
                "detail": "job job-1 already terminal: SUCCEEDED",
                "error_type": "runtime_state_conflict",
                "job_id": "job-1",
                "attempt_id": "attempt-1",
                "worker_id": "worker-1",
                "claim_token": "claim-1",
                "metadata_json": {},
            },
        )

    def test_fail_job_success_returns_contract(self) -> None:
        finished_at = datetime(2026, 4, 2, 12, 1, 0, tzinfo=timezone.utc)
        payload = {
            "job_id": "job-2",
            "attempt_id": "attempt-2",
            "worker_id": "worker-2",
            "claim_token": "claim-2",
            "next_job_status": "WAITING_RETRY",
            "attempt_terminal_status": "FAILED",
            "terminal_reason": "provider failed",
            "error_code": "PROVIDER_ERROR",
            "error_message": "provider failed",
            "error_payload_json": {"retryable": True},
            "expire_lease": False,
            "metadata_json": {"trace_id": "trace-2"},
        }
        result = {
            "job_id": "job-2",
            "attempt_id": "attempt-2",
            "lease_id": "lease-2",
            "job_status": "WAITING_RETRY",
            "attempt_status": "FAILED",
            "lease_status": "RELEASED",
            "worker_id": "worker-2",
            "current_job_count": 1,
            "finished_at": finished_at,
            "metadata_json": {"trace_id": "trace-2"},
        }

        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.fail_job.return_value = result
            facade_cls.return_value = facade

            response = self.client.post("/api/v1/runtime/terminal/fail", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "job_id": "job-2",
                "attempt_id": "attempt-2",
                "lease_id": "lease-2",
                "job_status": "WAITING_RETRY",
                "attempt_status": "FAILED",
                "lease_status": "RELEASED",
                "worker_id": "worker-2",
                "current_job_count": 1,
                "finished_at": "2026-04-02T12:01:00Z",
                "metadata_json": {"trace_id": "trace-2"},
            },
        )
        request_model = facade.fail_job.call_args.args[0]
        self.assertEqual(request_model.error_payload_json, {"retryable": True})
        self.assertFalse(request_model.expire_lease)

    def test_fail_job_maps_state_conflict_to_409(self) -> None:
        payload = {
            "job_id": "job-2",
            "attempt_id": "attempt-2",
            "worker_id": "worker-2",
            "claim_token": "claim-2",
            "next_job_status": "FAILED",
            "attempt_terminal_status": "FAILED",
        }

        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.fail_job.side_effect = RuntimeStateConflictError("job job-2 already terminal: FAILED")
            facade_cls.return_value = facade

            response = self.client.post("/api/v1/runtime/terminal/fail", json=payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {
                "detail": "job job-2 already terminal: FAILED",
                "error_type": "runtime_state_conflict",
                "job_id": "job-2",
                "attempt_id": "attempt-2",
                "worker_id": "worker-2",
                "claim_token": "claim-2",
                "metadata_json": {},
            },
        )

    def test_fail_job_maps_lease_conflict_to_409(self) -> None:
        payload = {
            "job_id": "job-2",
            "attempt_id": "attempt-2",
            "worker_id": "worker-2",
            "claim_token": "claim-2",
            "next_job_status": "FAILED",
            "attempt_terminal_status": "FAILED",
        }

        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.fail_job.side_effect = RuntimeLeaseConflictError("attempt worker_id mismatch")
            facade_cls.return_value = facade

            response = self.client.post("/api/v1/runtime/terminal/fail", json=payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {
                "detail": "attempt worker_id mismatch",
                "error_type": "runtime_lease_conflict",
                "job_id": "job-2",
                "attempt_id": "attempt-2",
                "worker_id": "worker-2",
                "claim_token": "claim-2",
                "metadata_json": {},
            },
        )

    def test_fail_job_rejects_invalid_next_job_status_with_422(self) -> None:
        payload = {
            "job_id": "job-2",
            "attempt_id": "attempt-2",
            "worker_id": "worker-2",
            "claim_token": "claim-2",
            "next_job_status": "SUCCEEDED",
            "attempt_terminal_status": "FAILED",
        }

        response = self.client.post("/api/v1/runtime/terminal/fail", json=payload)

        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertTrue(any("unsupported next_job_status: SUCCEEDED" in item["msg"] for item in detail))

    def test_fail_job_rejects_invalid_attempt_terminal_status_with_422(self) -> None:
        payload = {
            "job_id": "job-2",
            "attempt_id": "attempt-2",
            "worker_id": "worker-2",
            "claim_token": "claim-2",
            "next_job_status": "FAILED",
            "attempt_terminal_status": "COMPLETED",
        }

        response = self.client.post("/api/v1/runtime/terminal/fail", json=payload)

        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertTrue(any("unsupported attempt_terminal_status: COMPLETED" in item["msg"] for item in detail))

    def test_fail_job_stale_with_expire_lease_contract(self) -> None:
        finished_at = datetime(2026, 4, 2, 12, 2, 0, tzinfo=timezone.utc)
        payload = {
            "job_id": "job-3",
            "attempt_id": "attempt-3",
            "worker_id": "worker-3",
            "claim_token": "claim-3",
            "next_job_status": "STALE",
            "attempt_terminal_status": "STALE",
            "terminal_reason": "lease expired",
            "error_code": "LEASE_EXPIRED",
            "error_message": "worker heartbeat timed out",
            "expire_lease": True,
            "metadata_json": {"trace_id": "trace-3"},
        }
        result = {
            "job_id": "job-3",
            "attempt_id": "attempt-3",
            "lease_id": "lease-3",
            "job_status": "STALE",
            "attempt_status": "STALE",
            "lease_status": "EXPIRED",
            "worker_id": "worker-3",
            "current_job_count": 0,
            "finished_at": finished_at,
            "metadata_json": {"trace_id": "trace-3"},
        }

        with patch("app.api.v1.routes.runtime_terminal.RuntimeTerminalFacade") as facade_cls:
            facade = Mock()
            facade.fail_job.return_value = result
            facade_cls.return_value = facade

            response = self.client.post("/api/v1/runtime/terminal/fail", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "job_id": "job-3",
                "attempt_id": "attempt-3",
                "lease_id": "lease-3",
                "job_status": "STALE",
                "attempt_status": "STALE",
                "lease_status": "EXPIRED",
                "worker_id": "worker-3",
                "current_job_count": 0,
                "finished_at": "2026-04-02T12:02:00Z",
                "metadata_json": {"trace_id": "trace-3"},
            },
        )
        request_model = facade.fail_job.call_args.args[0]
        self.assertEqual(request_model.next_job_status, "STALE")
        self.assertEqual(request_model.attempt_terminal_status, "STALE")
        self.assertTrue(request_model.expire_lease)


if __name__ == "__main__":
    unittest.main()
