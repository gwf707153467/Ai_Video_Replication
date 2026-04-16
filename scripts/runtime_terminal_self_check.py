#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VENV_PYTHON = Path(sys.executable)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "tmp_runtime_terminal_self_check.json"
MODULES = [
    "app.schemas.runtime",
    "app.schemas",
    "app.services.runtime_terminal_facade",
    "app.api.v1.routes.runtime_terminal",
]
CHECK_DEFINITIONS = {
    "endpoint": {
        "result_name": "endpoint_suite",
        "kind": "subprocess",
        "command_tail": ["-m", "unittest", "discover", "-s", "tests", "-p", "test_runtime_terminal_endpoints.py"],
        "description": "Run runtime terminal endpoint contract suite.",
    },
    "workflow": {
        "result_name": "workflow_suite",
        "kind": "subprocess",
        "command_tail": ["-m", "unittest", "discover", "-s", "tests", "-p", "test_runtime_terminal_workflow.py"],
        "description": "Run frozen runtime terminal workflow suite.",
    },
    "imports": {
        "result_name": "import_self_check",
        "kind": "callable",
        "description": "Run terminal import self-check.",
    },
    "sdk": {
        "result_name": "sdk_regression_suite",
        "kind": "subprocess",
        "command_tail": ["-m", "unittest", "discover", "-s", "tests", "-p", "test_runtime_terminal_sdk*.py"],
        "description": "Run caller-side runtime terminal SDK regression slice.",
    },
}
DEFAULT_CHECK_KEYS = ["endpoint", "workflow", "imports", "sdk"]


@dataclass
class CheckResult:
    name: str
    status: str
    duration_seconds: float
    command: list[str] | None
    return_code: int | None
    stdout: str
    stderr: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 3),
            "command": self.command,
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "details": self.details,
        }


def run_subprocess_check(name: str, python_bin: str, command_tail: list[str]) -> CheckResult:
    started = time.monotonic()
    completed = subprocess.run(
        [python_bin, *command_tail],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    duration = time.monotonic() - started
    status = "passed" if completed.returncode == 0 else "failed"
    return CheckResult(
        name=name,
        status=status,
        duration_seconds=duration,
        command=[python_bin, *command_tail],
        return_code=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        details={},
    )


def run_import_check() -> CheckResult:
    started = time.monotonic()
    imported: list[str] = []
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        for module_name in MODULES:
            importlib.import_module(module_name)
            imported.append(module_name)
        duration = time.monotonic() - started
        return CheckResult(
            name="import_self_check",
            status="passed",
            duration_seconds=duration,
            command=None,
            return_code=0,
            stdout="\n".join(f"IMPORTED {name}" for name in imported),
            stderr="",
            details={"modules": imported},
        )
    except Exception as exc:  # pragma: no cover - defensive guardrail
        duration = time.monotonic() - started
        return CheckResult(
            name="import_self_check",
            status="failed",
            duration_seconds=duration,
            command=None,
            return_code=1,
            stdout="\n".join(f"IMPORTED {name}" for name in imported),
            stderr=f"{type(exc).__name__}: {exc}",
            details={
                "modules": imported,
                "failed_module": MODULES[len(imported)] if len(imported) < len(MODULES) else None,
            },
        )


def resolve_selected_checks(raw_checks: list[str] | None) -> list[str]:
    if not raw_checks:
        return list(DEFAULT_CHECK_KEYS)

    selected: list[str] = []
    for item in raw_checks:
        for token in item.split(","):
            normalized = token.strip().lower()
            if not normalized:
                continue
            if normalized == "all":
                for default_key in DEFAULT_CHECK_KEYS:
                    if default_key not in selected:
                        selected.append(default_key)
                continue
            if normalized not in CHECK_DEFINITIONS:
                valid = ", ".join([*CHECK_DEFINITIONS.keys(), "all"])
                raise ValueError(f"unsupported check '{normalized}'. valid values: {valid}")
            if normalized not in selected:
                selected.append(normalized)

    if not selected:
        return list(DEFAULT_CHECK_KEYS)
    return selected


def execute_selected_checks(selected_checks: list[str], python_bin: str) -> list[CheckResult]:
    callable_checks: dict[str, Callable[[], CheckResult]] = {
        "imports": run_import_check,
    }
    results: list[CheckResult] = []
    for check_key in selected_checks:
        definition = CHECK_DEFINITIONS[check_key]
        if definition["kind"] == "subprocess":
            results.append(
                run_subprocess_check(
                    name=str(definition["result_name"]),
                    python_bin=python_bin,
                    command_tail=list(definition["command_tail"]),
                )
            )
            continue
        results.append(callable_checks[check_key]())
    return results


def build_report(results: list[CheckResult], python_bin: str, selected_checks: list[str]) -> dict[str, Any]:
    overall_status = "passed" if all(result.status == "passed" for result in results) else "failed"
    selected_result_names = [str(CHECK_DEFINITIONS[key]["result_name"]) for key in selected_checks]
    return {
        "report_name": "runtime_terminal_self_check",
        "report_version": "v2",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "python_bin": python_bin,
        "selected_checks": selected_checks,
        "selected_result_names": selected_result_names,
        "overall_status": overall_status,
        "checks": [result.to_dict() for result in results],
    }


def print_summary(report: dict[str, Any]) -> None:
    print("=== Runtime Terminal Self Check ===")
    print(f"repo_root: {report['repo_root']}")
    print(f"python_bin: {report['python_bin']}")
    print(f"selected_checks: {', '.join(report['selected_checks'])}")
    print(f"overall_status: {report['overall_status']}")
    for check in report["checks"]:
        print(f"- {check['name']}: {check['status']} ({check['duration_seconds']}s)")
        if check["command"]:
            print(f"  command: {' '.join(check['command'])}")
        if check["stdout"]:
            print("  stdout:")
            for line in check["stdout"].splitlines():
                print(f"    {line}")
        if check["stderr"]:
            print("  stderr:")
            for line in check["stderr"].splitlines():
                print(f"    {line}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run runtime terminal smoke/self-check suite with selectable checks.")
    parser.add_argument(
        "--python-bin",
        default=str(DEFAULT_VENV_PYTHON),
        help="Python interpreter used for unittest checks. Default uses the currently active interpreter.",
    )
    parser.add_argument(
        "--check",
        action="append",
        default=None,
        help="Select checks to run. Repeatable or comma-separated. Supported values: endpoint, workflow, imports, sdk, all.",
    )
    parser.add_argument(
        "--list-checks",
        action="store_true",
        help="Print available checks and exit.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Optional JSON report path. Default writes to repo tmp_runtime_terminal_self_check.json.",
    )
    parser.add_argument(
        "--skip-json",
        action="store_true",
        help="Do not write JSON report to disk.",
    )
    return parser.parse_args()


def print_available_checks() -> None:
    print("Available runtime terminal self-check entries:")
    for key, definition in CHECK_DEFINITIONS.items():
        print(f"- {key}: {definition['result_name']} | {definition['description']}")
    print("- all: run endpoint, workflow, imports, sdk")


def main() -> int:
    args = parse_args()

    if args.list_checks:
        print_available_checks()
        return 0

    try:
        selected_checks = resolve_selected_checks(args.check)
    except ValueError as exc:
        print(f"argument error: {exc}", file=sys.stderr)
        return 2

    python_bin = args.python_bin
    results = execute_selected_checks(selected_checks, python_bin)
    report = build_report(results, python_bin, selected_checks)

    if not args.skip_json:
        output_path = Path(args.output_json)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print_summary(report)
    return 0 if report["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
