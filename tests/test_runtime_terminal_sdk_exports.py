from __future__ import annotations

import inspect
import unittest

import app.runtime_terminal_sdk as runtime_terminal_sdk
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


class RuntimeTerminalSdkExportsTests(unittest.TestCase):
    def test_package___all___matches_frozen_public_surface(self) -> None:
        self.assertEqual(
            runtime_terminal_sdk.__all__,
            [
                "RuntimeAttemptContext",
                "RuntimeTerminalClient",
                "RuntimeTerminalError",
                "RuntimeTerminalNotFoundError",
                "RuntimeTerminalConflictError",
                "RuntimeTerminalValidationError",
                "RuntimeTerminalServerError",
                "RuntimeTerminalTransportError",
            ],
        )

    def test_package_level_imports_resolve_to_expected_symbols(self) -> None:
        self.assertIs(runtime_terminal_sdk.RuntimeAttemptContext, RuntimeAttemptContext)
        self.assertIs(runtime_terminal_sdk.RuntimeTerminalClient, RuntimeTerminalClient)
        self.assertIs(runtime_terminal_sdk.RuntimeTerminalError, RuntimeTerminalError)
        self.assertIs(runtime_terminal_sdk.RuntimeTerminalNotFoundError, RuntimeTerminalNotFoundError)
        self.assertIs(runtime_terminal_sdk.RuntimeTerminalConflictError, RuntimeTerminalConflictError)
        self.assertIs(runtime_terminal_sdk.RuntimeTerminalValidationError, RuntimeTerminalValidationError)
        self.assertIs(runtime_terminal_sdk.RuntimeTerminalServerError, RuntimeTerminalServerError)
        self.assertIs(runtime_terminal_sdk.RuntimeTerminalTransportError, RuntimeTerminalTransportError)

    def test_runtime_attempt_context_shape_remains_minimal_and_stable(self) -> None:
        signature = inspect.signature(RuntimeAttemptContext)
        self.assertEqual(
            list(signature.parameters.keys()),
            ["job_id", "attempt_id", "worker_id", "claim_token"],
        )

    def test_runtime_terminal_client_public_methods_remain_minimal(self) -> None:
        public_callables = sorted(
            name
            for name, value in RuntimeTerminalClient.__dict__.items()
            if callable(value) and not name.startswith("_")
        )
        self.assertEqual(
            public_callables,
            ["complete_job", "fail_job", "get_job_snapshot"],
        )

    def test_runtime_terminal_client_constructor_surface_is_stable(self) -> None:
        signature = inspect.signature(RuntimeTerminalClient)
        self.assertEqual(
            list(signature.parameters.keys()),
            ["base_url", "timeout_seconds", "session"],
        )

    def test_minimal_exception_tree_stays_package_visible(self) -> None:
        self.assertTrue(issubclass(RuntimeTerminalNotFoundError, RuntimeTerminalError))
        self.assertTrue(issubclass(RuntimeTerminalConflictError, RuntimeTerminalError))
        self.assertTrue(issubclass(RuntimeTerminalValidationError, RuntimeTerminalError))
        self.assertTrue(issubclass(RuntimeTerminalServerError, RuntimeTerminalError))
        self.assertTrue(issubclass(RuntimeTerminalTransportError, RuntimeTerminalError))


if __name__ == "__main__":
    unittest.main()
