#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_MODEL = "veo-3.1-generate-preview"
DEFAULT_DURATIONS = [4, 5, 6, 8]
DEFAULT_CASE_ID = "case-001"
DEFAULT_HISTORY_EVIDENCE_DIR = (
    ".evidence/case-001/render-video-gemini-compat-request-capture-20260420T153612Z"
)
DEFAULT_PROMPT = (
    "Create a premium TikTok beauty product hero image on pure white background, serum bottle centered vertically, "
    "clean studio lighting, realistic packaging detail, high-end cosmetic advertising look, 9:16 composition.\n\n"
    "Project ID: 656ac6b1-ecb8-4f45-9f45-556be5915168\n\n"
    "Sequence type: hook\n\n"
    "Persuasive goal: Introduce the beauty product with a clean premium visual\n\n"
    "SPU display name: Beauty serum hero shot\n\n"
    "Visual constraints: style=studio_clean, platform=tiktok_9_16, background=#FFFFFF"
)
DEFAULT_NEGATIVE_PROMPT = (
    "blurry, deformed packaging, extra objects, cropped product, watermark, text overlay"
)
DEFAULT_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "veo-3.1-generate-preview:predictLongRunning"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] {message}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a minimal direct Google/Veo duration matrix experiment for case-001."
    )
    parser.add_argument(
        "--evidence-dir",
        required=True,
        help="Evidence directory to write experiment artifacts into.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Google API key. If omitted, GEMINI_API_KEY or GOOGLE_API_KEY will be used.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Video model name. Default: veo-3.1-generate-preview",
    )
    parser.add_argument(
        "--durations",
        default=",".join(str(value) for value in DEFAULT_DURATIONS),
        help="Comma-separated durationSeconds values. Default: 4,5,6,8",
    )
    parser.add_argument(
        "--prompt-file",
        default=None,
        help="Optional path to a UTF-8 prompt text file. If omitted, the historical captured prompt is used.",
    )
    parser.add_argument(
        "--negative-prompt-file",
        default=None,
        help="Optional path to a UTF-8 negative prompt text file. If omitted, the historical captured negative prompt is used.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=1,
        help="number_of_videos for GenerateVideosConfig. Default: 1",
    )
    parser.add_argument(
        "--skip-poll",
        action="store_true",
        help="Only submit generate_videos and do not poll/download. Recommended for request-acceptance boundary checks.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=5.0,
        help="Polling interval if polling is enabled. Default: 5.0",
    )
    parser.add_argument(
        "--max-polls",
        type=int,
        default=1,
        help="Max polls if polling is enabled. Default: 1",
    )
    return parser.parse_args()


def load_text_file(path: str | None, fallback: str) -> str:
    if not path:
        return fallback
    return Path(path).read_text(encoding="utf-8")


def resolve_api_key(cli_value: str | None) -> str:
    value = cli_value or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    normalized = str(value or "").strip()
    if not normalized:
        raise SystemExit("Missing API key. Provide --api-key or set GEMINI_API_KEY/GOOGLE_API_KEY.")
    return normalized


def parse_durations(raw: str) -> list[int]:
    values: list[int] = []
    for part in raw.split(","):
        normalized = part.strip()
        if not normalized:
            continue
        values.append(int(normalized))
    if not values:
        raise SystemExit("At least one duration value is required.")
    return values


def sanitize_exception(exc: BaseException) -> dict[str, Any]:
    return {
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc(),
    }


def summarize_operation(operation: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "operation_type": type(operation).__name__,
        "done": getattr(operation, "done", None),
        "name": getattr(operation, "name", None),
    }
    response = getattr(operation, "response", None)
    result = getattr(operation, "result", None)
    error = getattr(operation, "error", None)
    metadata = getattr(operation, "metadata", None)
    if response is not None:
        summary["response_type"] = type(response).__name__
    if result is not None:
        summary["result_type"] = type(result).__name__
    if metadata is not None:
        summary["metadata_type"] = type(metadata).__name__
    if error is not None:
        summary["error"] = {
            "type": type(error).__name__,
            "repr": repr(error),
            "code": getattr(error, "code", None),
            "message": getattr(error, "message", None),
        }
    return summary


def build_request_body(prompt: str, negative_prompt: str | None, sample_count: int, duration_seconds: int) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "sampleCount": sample_count,
        "durationSeconds": duration_seconds,
    }
    if negative_prompt:
        parameters["negativePrompt"] = negative_prompt
    return {
        "instances": [{"prompt": prompt}],
        "parameters": parameters,
    }


def detect_sdk_version() -> str | None:
    try:
        import google.genai  # type: ignore
    except Exception:
        return None
    return getattr(google.genai, "__version__", None)


def submit_one_duration(
    *,
    api_key: str,
    model: str,
    prompt: str,
    negative_prompt: str | None,
    sample_count: int,
    duration_seconds: int,
    skip_poll: bool,
    poll_interval_seconds: float,
    max_polls: int,
) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    captured_at = utc_now()
    request_body = build_request_body(prompt, negative_prompt, sample_count, duration_seconds)
    config = types.GenerateVideosConfig(
        number_of_videos=sample_count,
        negative_prompt=negative_prompt,
        duration_seconds=duration_seconds,
    )
    payload: dict[str, Any] = {
        "captured_at": captured_at,
        "api_surface": "generative-language-v1beta-via-google-genai",
        "sdk_version": detect_sdk_version(),
        "model": model,
        "request_url": (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predictLongRunning"
        ),
        "duration_seconds": duration_seconds,
        "sample_count": sample_count,
        "negative_prompt_present": bool(negative_prompt),
        "prompt_length": len(prompt),
        "skip_poll": skip_poll,
        "poll_interval_seconds": poll_interval_seconds,
        "max_polls": max_polls,
        "config_dump": config.model_dump(exclude_none=True),
        "request_body_expected": request_body,
    }

    client = genai.Client(api_key=api_key)
    try:
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=config,
        )
        payload["submit_ok"] = True
        payload["submit_operation"] = summarize_operation(operation)
        if skip_poll:
            payload["ok"] = True
            payload["result_mode"] = "submit_only"
            return payload

        current_operation = operation
        for poll_index in range(max_polls):
            if getattr(current_operation, "done", False):
                break
            current_operation = client.operations.get(operation=current_operation)
            payload.setdefault("polls", []).append(
                {
                    "poll_index": poll_index + 1,
                    "observed_at": utc_now(),
                    "operation": summarize_operation(current_operation),
                }
            )
            if getattr(current_operation, "done", False):
                break
            if poll_index + 1 < max_polls:
                import time
                time.sleep(poll_interval_seconds)

        payload["final_operation"] = summarize_operation(current_operation)
        payload["ok"] = True
        payload["result_mode"] = "submit_and_poll"
        return payload
    except Exception as exc:
        payload["ok"] = False
        payload.update(sanitize_exception(exc))
        return payload


def classify_pattern(results: list[dict[str, Any]]) -> str:
    if results and all(item.get("ok") for item in results):
        return "all_succeeded"
    error_messages = [str(item.get("error_message") or "") for item in results if not item.get("ok")]
    boundary_errors = [msg for msg in error_messages if "durationSeconds" in msg and "out of bound" in msg]
    failed_durations = [int(item["duration_seconds"]) for item in results if not item.get("ok")]
    if failed_durations == [5] and len(results) == 4:
        return "only_5_failed"
    if boundary_errors and len(boundary_errors) == len(results):
        return "all_failed_same_boundary_error"
    if failed_durations:
        return "partial_failed_mixed"
    return "inconclusive"


def main() -> int:
    args = parse_args()
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = evidence_dir / "run_log.txt"
    api_key = resolve_api_key(args.api_key)
    prompt = load_text_file(args.prompt_file, DEFAULT_PROMPT).strip()
    negative_prompt = load_text_file(args.negative_prompt_file, DEFAULT_NEGATIVE_PROMPT).strip()
    durations = parse_durations(args.durations)

    plan = {
        "created_at": utc_now(),
        "case_id": DEFAULT_CASE_ID,
        "objective": (
            "Minimal direct Google/Veo duration matrix experiment against the same model/account/API surface, "
            "varying only durationSeconds across 4/5/6/8."
        ),
        "history_evidence_dir": DEFAULT_HISTORY_EVIDENCE_DIR,
        "fixed_inputs": {
            "model": args.model,
            "request_url": f"https://generativelanguage.googleapis.com/v1beta/models/{args.model}:predictLongRunning",
            "sample_count": args.sample_count,
            "skip_poll": args.skip_poll,
            "prompt_length": len(prompt),
            "negative_prompt_present": bool(negative_prompt),
        },
        "durations": durations,
        "expected_reference_request_url": DEFAULT_ENDPOINT,
    }
    write_json(evidence_dir / "experiment_plan.json", plan)
    append_log(log_path, f"Experiment initialized for durations={durations} model={args.model}")

    results: list[dict[str, Any]] = []
    for duration_seconds in durations:
        append_log(log_path, f"Submitting durationSeconds={duration_seconds}")
        result = submit_one_duration(
            api_key=api_key,
            model=args.model,
            prompt=prompt,
            negative_prompt=negative_prompt,
            sample_count=args.sample_count,
            duration_seconds=duration_seconds,
            skip_poll=args.skip_poll,
            poll_interval_seconds=args.poll_interval_seconds,
            max_polls=args.max_polls,
        )
        write_json(evidence_dir / f"sdk_duration_{duration_seconds}.json", result)
        append_log(
            log_path,
            "Completed durationSeconds="
            f"{duration_seconds} ok={result.get('ok')} error={result.get('error_message')}",
        )
        results.append(
            {
                "duration_seconds": duration_seconds,
                "ok": result.get("ok"),
                "submit_ok": result.get("submit_ok"),
                "status_code": result.get("status_code"),
                "error_type": result.get("error_type"),
                "error_message": result.get("error_message"),
                "operation_name": (
                    (result.get("final_operation") or {}).get("name")
                    or (result.get("submit_operation") or {}).get("name")
                ),
            }
        )

    summary = {
        "collected_at": utc_now(),
        "model": args.model,
        "api_surface": "generative-language-v1beta-via-google-genai",
        "sdk_version": detect_sdk_version(),
        "durations_tested": durations,
        "results": results,
        "pattern": classify_pattern(results),
    }
    write_json(evidence_dir / "duration_matrix_summary.json", summary)

    assessment_lines = [
        "# FINAL ASSESSMENT",
        "",
        f"- model: `{args.model}`",
        "- api_surface: `generative-language-v1beta-via-google-genai`",
        f"- durations_tested: `{durations}`",
        f"- pattern: `{summary['pattern']}`",
        "",
        "## Matrix",
        "",
    ]
    for item in results:
        assessment_lines.append(
            f"- duration={item['duration_seconds']}: ok={item['ok']}, error_type={item['error_type']}, error_message={item['error_message']}"
        )
    assessment_lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This assessment is limited to request-acceptance behavior under the current account/model/API surface. "
            "It does not infer that local duration propagation was wrong, because historical evidence already fixed the outbound request body at durationSeconds=5.",
        ]
    )
    (evidence_dir / "FINAL_ASSESSMENT.md").write_text("\n".join(assessment_lines) + "\n", encoding="utf-8")
    append_log(log_path, f"Experiment completed with pattern={summary['pattern']}")
    print(json.dumps({"evidence_dir": str(evidence_dir), "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
