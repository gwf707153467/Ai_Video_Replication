from __future__ import annotations

import json
import unittest
from uuid import UUID

import httpx

from app.runtime_terminal_sdk import (
    RuntimeAttemptContext,
    RuntimeTerminalClient,
    RuntimeTerminalConflictError,
    RuntimeTerminalError,
    RuntimeTerminalNotFoundError,
    RuntimeTerminalServerError,
    RuntimeTerminalTransportError,
    RuntimeTerminalValidationError,
)


class RuntimeTerminalSdkClientTests(unittest.TestCase):
    def _build_context(self) -> RuntimeAttemptContext:
        return RuntimeAttemptContext(
            job_id="job-123",
            attempt_id="attempt-123",
            worker_id="worker-123",
            claim_token="claim-123",
        )

    def _build_client(
        self,
        handler,
        *,
        base_url: str = "https://runtime.example.internal/",
        timeout_seconds: float = 12.5,
    ) -> RuntimeTerminalClient:
        transport = httpx.MockTransport(handler)
        session = httpx.Client(transport=transport)
        self.addCleanup(session.close)
        return RuntimeTerminalClient(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            session=session,
        )

    def test_complete_job_success_path_and_strict_passthrough(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["url"] = str(request.url)
            captured["json"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={"job_status": "succeeded", "attempt_status": "completed"},
            )

        client = self._build_client(handler)
        ctx = self._build_context()

        result = client.complete_job(
            ctx,
            completion_status="succeeded",
            terminal_reason="done",
            result_ref="minio://bucket/job-123.json",
            manifest_artifact_id=UUID("12345678-1234-5678-1234-567812345678"),
            runtime_ms=101,
            provider_runtime_ms=88,
            upload_ms=13,
            metadata_json=None,
        )

        self.assertEqual(result, {"job_status": "succeeded", "attempt_status": "completed"})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            "https://runtime.example.internal/api/v1/runtime/terminal/complete",
        )
        self.assertEqual(
            captured["json"],
            {
                "job_id": "job-123",
                "attempt_id": "attempt-123",
                "worker_id": "worker-123",
                "claim_token": "claim-123",
                "completion_status": "succeeded",
                "terminal_reason": "done",
                "result_ref": "minio://bucket/job-123.json",
                "manifest_artifact_id": "12345678-1234-5678-1234-567812345678",
                "runtime_ms": 101,
                "provider_runtime_ms": 88,
                "upload_ms": 13,
                "metadata_json": None,
            },
        )

    def test_fail_job_success_path_and_strict_passthrough(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["url"] = str(request.url)
            captured["json"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={"job_status": "failed", "attempt_status": "failed"},
            )

        client = self._build_client(handler, base_url="https://runtime.example.internal")
        ctx = self._build_context()

        result = client.fail_job(
            ctx,
            next_job_status="failed",
            attempt_terminal_status="failed",
            terminal_reason="provider_error",
            error_code="UPSTREAM_500",
            error_message="provider failed",
            error_payload_json=None,
            expire_lease=False,
            metadata_json=None,
        )

        self.assertEqual(result, {"job_status": "failed", "attempt_status": "failed"})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            "https://runtime.example.internal/api/v1/runtime/terminal/fail",
        )
        self.assertEqual(
            captured["json"],
            {
                "job_id": "job-123",
                "attempt_id": "attempt-123",
                "worker_id": "worker-123",
                "claim_token": "claim-123",
                "next_job_status": "failed",
                "attempt_terminal_status": "failed",
                "terminal_reason": "provider_error",
                "error_code": "UPSTREAM_500",
                "error_message": "provider failed",
                "error_payload_json": None,
                "expire_lease": False,
                "metadata_json": None,
            },
        )

    def test_get_job_snapshot_success_path(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["url"] = str(request.url)
            return httpx.Response(
                200,
                json={"job_id": "job-123", "job_status": "running"},
            )

        client = self._build_client(handler)

        result = client.get_job_snapshot("job-123")

        self.assertEqual(result, {"job_id": "job-123", "job_status": "running"})
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(
            captured["url"],
            "https://runtime.example.internal/api/v1/runtime/terminal/jobs/job-123",
        )

    def test_request_maps_404_to_not_found(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text='{"detail":"missing"}')

        client = self._build_client(handler)

        with self.assertRaises(RuntimeTerminalNotFoundError) as exc_info:
            client.get_job_snapshot("job-missing")

        exc = exc_info.exception
        self.assertEqual(exc.status_code, 404)
        self.assertEqual(exc.method, "GET")
        self.assertEqual(exc.path, "/api/v1/runtime/terminal/jobs/job-missing")
        self.assertEqual(exc.response_text, '{"detail":"missing"}')

    def test_request_maps_409_to_conflict(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(409, text='{"detail":"conflict"}')

        client = self._build_client(handler)

        with self.assertRaises(RuntimeTerminalConflictError) as exc_info:
            client.complete_job(self._build_context(), completion_status="succeeded")

        exc = exc_info.exception
        self.assertEqual(exc.status_code, 409)
        self.assertEqual(exc.method, "POST")
        self.assertEqual(exc.path, "/api/v1/runtime/terminal/complete")
        self.assertEqual(exc.response_text, '{"detail":"conflict"}')

    def test_request_maps_422_to_validation_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(422, text='{"detail":"invalid payload"}')

        client = self._build_client(handler)

        with self.assertRaises(RuntimeTerminalValidationError) as exc_info:
            client.fail_job(
                self._build_context(),
                next_job_status="failed",
                attempt_terminal_status="failed",
            )

        exc = exc_info.exception
        self.assertEqual(exc.status_code, 422)
        self.assertEqual(exc.method, "POST")
        self.assertEqual(exc.path, "/api/v1/runtime/terminal/fail")
        self.assertEqual(exc.response_text, '{"detail":"invalid payload"}')

    def test_request_maps_5xx_to_server_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="service unavailable")

        client = self._build_client(handler)

        with self.assertRaises(RuntimeTerminalServerError) as exc_info:
            client.get_job_snapshot("job-123")

        exc = exc_info.exception
        self.assertEqual(exc.status_code, 503)
        self.assertEqual(exc.method, "GET")
        self.assertEqual(exc.path, "/api/v1/runtime/terminal/jobs/job-123")
        self.assertEqual(exc.response_text, "service unavailable")

    def test_request_maps_other_4xx_to_base_runtime_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="unauthorized")

        client = self._build_client(handler)

        with self.assertRaises(RuntimeTerminalError) as exc_info:
            client.get_job_snapshot("job-123")

        exc = exc_info.exception
        self.assertIsInstance(exc, RuntimeTerminalError)
        self.assertEqual(type(exc), RuntimeTerminalError)
        self.assertEqual(exc.status_code, 401)
        self.assertEqual(exc.method, "GET")
        self.assertEqual(exc.path, "/api/v1/runtime/terminal/jobs/job-123")
        self.assertEqual(exc.response_text, "unauthorized")

    def test_transport_error_is_mapped_separately_from_http_semantic_errors(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        client = self._build_client(handler)

        with self.assertRaises(RuntimeTerminalTransportError) as exc_info:
            client.get_job_snapshot("job-123")

        exc = exc_info.exception
        self.assertIsNone(exc.status_code)
        self.assertEqual(exc.method, "GET")
        self.assertEqual(exc.path, "/api/v1/runtime/terminal/jobs/job-123")
        self.assertIsNone(exc.response_text)
        self.assertIsInstance(exc.__cause__, httpx.ReadTimeout)

    def test_non_json_success_response_is_treated_as_server_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="ok but not json")

        client = self._build_client(handler)

        with self.assertRaises(RuntimeTerminalServerError) as exc_info:
            client.get_job_snapshot("job-123")

        exc = exc_info.exception
        self.assertEqual(exc.status_code, 200)
        self.assertEqual(exc.method, "GET")
        self.assertEqual(exc.path, "/api/v1/runtime/terminal/jobs/job-123")
        self.assertEqual(exc.response_text, "ok but not json")


if __name__ == "__main__":
    unittest.main()
