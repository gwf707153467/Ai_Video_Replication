from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPO_ROOT / ".evidence" / "regression"
DEFAULT_CASE_PAYLOAD = REPO_ROOT / ".evidence" / "case-001" / "compile_request_payload.json"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@dataclass
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_command(name: str, command: list[str]) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return CommandResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local regression suite.")
    parser.add_argument(
        "--case-payload",
        action="append",
        dest="case_payloads",
        help="Path to a compile payload json. Can be provided multiple times.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="How many times to run each case payload.",
    )
    parser.add_argument(
        "--case-delay-seconds",
        type=int,
        default=0,
        help="Seconds to wait between case runs to avoid provider rate limits.",
    )
    parser.add_argument(
        "--skip-baseline-gate",
        action="store_true",
        help="Skip baseline gate execution.",
    )
    parser.add_argument(
        "--skip-unit-tests",
        action="store_true",
        help="Skip targeted unittest execution.",
    )
    return parser.parse_args()


def normalize_payloads(case_payloads: list[str] | None) -> list[Path]:
    if not case_payloads:
        return [DEFAULT_CASE_PAYLOAD]
    return [Path(item).resolve() for item in case_payloads]


def case_name_for_payload(payload_path: Path, iteration: int) -> str:
    parent_name = payload_path.parent.name
    if parent_name:
        return f"{parent_name}-run-{iteration}"
    return f"{payload_path.stem}-run-{iteration}"


def render_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Regression Suite")
    lines.append("")
    lines.append(f"- executed_at: `{summary['executed_at']}`")
    lines.append(f"- suite_status: `{summary['suite_status']}`")
    lines.append("")

    baseline_gate = summary.get("baseline_gate")
    if baseline_gate:
        lines.append("## Baseline Gate")
        lines.append("")
        lines.append(f"- status: `{baseline_gate['status']}`")
        lines.append(f"- output_json: `{baseline_gate.get('output_json')}`")
        lines.append("")

    unit_tests = summary.get("unit_tests")
    if unit_tests:
        lines.append("## Unit Tests")
        lines.append("")
        lines.append(f"- status: `{unit_tests['status']}`")
        lines.append(f"- command: `{unit_tests['command']}`")
        lines.append("")

    lines.append("## Cases")
    lines.append("")
    for case in summary.get("cases", []):
        lines.append(f"### {case['name']}")
        lines.append("")
        lines.append(f"- payload: `{case['payload']}`")
        lines.append(f"- status: `{case['status']}`")
        lines.append(f"- runtime_version: `{case.get('runtime_version')}`")
        lines.append(f"- evidence_dir: `{case.get('evidence_dir')}`")
        lines.append(f"- final_output_exists: `{case.get('final_output_exists')}`")
        if case.get("last_error_code") or case.get("last_error_message"):
            lines.append(f"- last_error_code: `{case.get('last_error_code')}`")
            lines.append(f"- last_error_message: `{case.get('last_error_message')}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_quota_blocked(snapshot: dict[str, Any]) -> bool:
    runtime_record = snapshot.get("runtime_record") if isinstance(snapshot, dict) else {}
    message = str((runtime_record or {}).get("last_error_message") or "")
    code = str((runtime_record or {}).get("last_error_code") or "")
    return (
        "RESOURCE_EXHAUSTED" in message
        or "429" in message
        or "quota" in message.lower()
        or code == "resource_exhausted"
    )


def merge_suite_status(current: str, case_status: str) -> str:
    if current == "FAIL" or case_status == "FAIL":
        return "FAIL"
    if current == "INCONCLUSIVE" or case_status == "QUOTA_BLOCKED":
        return "INCONCLUSIVE"
    return current


def main() -> int:
    args = parse_args()
    run_id = utc_timestamp()
    suite_dir = EVIDENCE_ROOT / run_id
    suite_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "suite_status": "PASS",
        "baseline_gate": None,
        "unit_tests": None,
        "cases": [],
    }

    if not args.skip_baseline_gate:
        output_json = suite_dir / "baseline_gate_verdict.json"
        output_md = suite_dir / "baseline_gate_verdict.md"
        result = run_command(
            "baseline_gate",
            [
                sys.executable,
                "scripts/baseline_gate.py",
                "--output-json",
                str(output_json),
                "--output-md",
                str(output_md),
            ],
        )
        write_text(suite_dir / "baseline_gate.stdout.log", result.stdout)
        write_text(suite_dir / "baseline_gate.stderr.log", result.stderr)
        baseline_status = "PASS" if result.ok else "FAIL"
        summary["baseline_gate"] = {
            "status": baseline_status,
            "command": " ".join(result.command),
            "output_json": str(output_json),
            "output_md": str(output_md),
        }
        if not result.ok:
            summary["suite_status"] = "FAIL"

    if not args.skip_unit_tests:
        result = run_command(
            "unit_tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "tests.test_google_provider_client",
                "tests.test_worker_execution_guards",
            ],
        )
        write_text(suite_dir / "unit_tests.stdout.log", result.stdout)
        write_text(suite_dir / "unit_tests.stderr.log", result.stderr)
        unit_status = "PASS" if result.ok else "FAIL"
        summary["unit_tests"] = {
            "status": unit_status,
            "command": " ".join(result.command),
        }
        if not result.ok:
            summary["suite_status"] = "FAIL"

    case_run_index = 0
    for payload_path in normalize_payloads(args.case_payloads):
        for iteration in range(1, max(1, args.repeat) + 1):
            if case_run_index > 0 and args.case_delay_seconds > 0:
                time.sleep(args.case_delay_seconds)
            case_run_index += 1
            case_name = case_name_for_payload(payload_path, iteration)
            evidence_dir = suite_dir / case_name
            final_output = evidence_dir / "final_output.mp4"
            result = run_command(
                case_name,
                [
                    sys.executable,
                    "scripts/case_001_real_run_collect.py",
                    "--payload",
                    str(payload_path),
                    "--evidence-dir",
                    str(evidence_dir),
                    "--final-output",
                    str(final_output),
                ],
            )
            write_text(evidence_dir / "case.stdout.log", result.stdout)
            write_text(evidence_dir / "case.stderr.log", result.stderr)

            run_summary_path = evidence_dir / "run_summary.json"
            run_summary = load_json_if_exists(run_summary_path)
            runtime_snapshot = load_json_if_exists(evidence_dir / "runtime_snapshot_final.json")

            if (
                result.ok
                and run_summary.get("terminal_compile_status") == "succeeded"
                and run_summary.get("final_output_exists") is True
            ):
                case_status = "PASS"
            elif is_quota_blocked(runtime_snapshot):
                case_status = "QUOTA_BLOCKED"
            else:
                case_status = "FAIL"

            runtime_record = runtime_snapshot.get("runtime_record", {}) if runtime_snapshot else {}
            summary["cases"].append(
                {
                    "name": case_name,
                    "payload": str(payload_path),
                    "status": case_status,
                    "runtime_version": run_summary.get("runtime_version"),
                    "evidence_dir": str(evidence_dir),
                    "final_output_exists": run_summary.get("final_output_exists"),
                    "last_error_code": runtime_record.get("last_error_code"),
                    "last_error_message": runtime_record.get("last_error_message"),
                }
            )
            summary["suite_status"] = merge_suite_status(summary["suite_status"], case_status)

    write_json(suite_dir / "regression_summary.json", summary)
    write_text(suite_dir / "regression_summary.md", render_markdown(summary))
    print(
        json.dumps(
            {
                "suite_status": summary["suite_status"],
                "suite_dir": str(suite_dir),
            },
            ensure_ascii=False,
        )
    )
    return 0 if summary["suite_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
