#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.providers.google.client import GoogleProviderClient, GoogleProviderError

DEFAULT_OUTPUT_JSON = REPO_ROOT / "tmp_relay_smoke.json"
DEFAULT_IMAGE_PROMPT = "Generate a clean product hero image of a luxury handbag on a studio background."
DEFAULT_VIDEO_PROMPT = "Create a short product showcase video of a luxury handbag with gentle camera motion and soft studio lighting."
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_POLL_INTERVAL_SECONDS = 15.0
DEFAULT_IMAGE_ASPECT_RATIO = "1:1"
DEFAULT_VIDEO_ASPECT_RATIO = "9:16"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_secret(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    if len(normalized) <= 8:
        return "*" * len(normalized)
    return f"{normalized[:4]}...{normalized[-4:]}"


def resolve_api_key(cli_value: str | None) -> str:
    for candidate in [cli_value, os.getenv("GOOGLE_API_KEY"), os.getenv("GEMINI_API_KEY")]:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


def resolve_model(cli_value: str | None, env_name: str) -> str:
    for candidate in [cli_value, os.getenv(env_name)]:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


def build_client(args: argparse.Namespace) -> GoogleProviderClient:
    api_key = resolve_api_key(args.api_key)
    image_model = resolve_model(args.image_model, "GOOGLE_IMAGE_MODEL")
    video_model = resolve_model(args.video_model, "GOOGLE_VIDEO_MODEL")
    tts_model = resolve_model(None, "GOOGLE_TTS_MODEL")

    client = GoogleProviderClient(
        api_key=api_key,
        video_model=video_model,
        image_model=image_model,
        tts_model=tts_model,
    )
    client.video_poll_interval_seconds = float(args.poll_interval_seconds)
    client.video_max_polls = max(1, int(args.timeout_seconds / max(args.poll_interval_seconds, 0.1)))
    return client


def run_image_smoke(client: GoogleProviderClient, args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    started_at = utc_now_iso()
    try:
        result = client.generate_image(
            prompt=args.image_prompt,
            sample_count=1,
            aspect_ratio=args.image_aspect_ratio,
        )
        return {
            "status": "passed",
            "started_at": started_at,
            "duration_seconds": round(time.monotonic() - started, 3),
            "content_type": result.content_type,
            "byte_length": len(result.image_bytes),
            "provider_payload": result.provider_payload,
        }
    except GoogleProviderError as exc:
        return {
            "status": "failed",
            "started_at": started_at,
            "duration_seconds": round(time.monotonic() - started, 3),
            "error": {
                "type": type(exc).__name__,
                "code": exc.code,
                "message": exc.message,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive guardrail
        return {
            "status": "failed",
            "started_at": started_at,
            "duration_seconds": round(time.monotonic() - started, 3),
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }


def run_video_smoke(client: GoogleProviderClient, args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    started_at = utc_now_iso()
    try:
        result = client.generate_video(
            prompt=args.video_prompt,
            sample_count=1,
            aspect_ratio=args.video_aspect_ratio,
            poll_interval_seconds=args.poll_interval_seconds,
            max_polls=max(1, int(args.timeout_seconds / max(args.poll_interval_seconds, 0.1))),
        )
        return {
            "status": "passed",
            "started_at": started_at,
            "duration_seconds": round(time.monotonic() - started, 3),
            "content_type": result.content_type,
            "byte_length": len(result.video_bytes),
            "provider_payload": result.provider_payload,
        }
    except GoogleProviderError as exc:
        return {
            "status": "failed",
            "started_at": started_at,
            "duration_seconds": round(time.monotonic() - started, 3),
            "error": {
                "type": type(exc).__name__,
                "code": exc.code,
                "message": exc.message,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive guardrail
        return {
            "status": "failed",
            "started_at": started_at,
            "duration_seconds": round(time.monotonic() - started, 3),
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }


def build_report(args: argparse.Namespace, client: GoogleProviderClient) -> dict[str, Any]:
    image_result = run_image_smoke(client, args)
    video_result = run_video_smoke(client, args)
    overall_status = "passed" if image_result["status"] == "passed" and video_result["status"] == "passed" else "failed"
    return {
        "report_name": "relay_smoke",
        "report_version": "v1",
        "executed_at": utc_now_iso(),
        "repo_root": str(REPO_ROOT),
        "relay_base_url": client.relay_base_url,
        "overall_status": overall_status,
        "config": {
            "api_key_present": bool(client.api_key),
            "api_key_masked": mask_secret(client.api_key),
            "image_model": client.image_model,
            "video_model": client.video_model,
            "tts_model": client.tts_model,
            "image_aspect_ratio": args.image_aspect_ratio,
            "video_aspect_ratio": args.video_aspect_ratio,
            "timeout_seconds": float(args.timeout_seconds),
            "poll_interval_seconds": float(args.poll_interval_seconds),
        },
        "checks": {
            "image_create": image_result,
            "video_create_poll": video_result,
        },
    }


def print_summary(report: dict[str, Any]) -> None:
    print("=== Relay Smoke ===")
    print(f"relay_base_url: {report['relay_base_url']}")
    print(f"overall_status: {report['overall_status']}")
    config = report["config"]
    print(f"api_key_present: {config['api_key_present']}")
    print(f"api_key_masked: {config['api_key_masked']}")
    print(f"image_model: {config['image_model']}")
    print(f"video_model: {config['video_model']}")
    print(f"timeout_seconds: {config['timeout_seconds']}")
    print(f"poll_interval_seconds: {config['poll_interval_seconds']}")
    for check_name, check in report["checks"].items():
        print(f"- {check_name}: {check['status']} ({check['duration_seconds']}s)")
        if check.get("content_type"):
            print(f"  content_type: {check['content_type']}")
        if check.get("byte_length") is not None:
            print(f"  byte_length: {check['byte_length']}")
        if check.get("error"):
            error = check["error"]
            print(f"  error_type: {error.get('type', '')}")
            if error.get("code"):
                print(f"  error_code: {error['code']}")
            print(f"  error_message: {error.get('message', '')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run minimal Relay-backed image create and video create+poll smoke checks.")
    parser.add_argument("--api-key", default=None, help="Optional Relay API key override. Falls back to GOOGLE_API_KEY, then GEMINI_API_KEY.")
    parser.add_argument("--image-prompt", default=DEFAULT_IMAGE_PROMPT, help="Prompt used for the image smoke request.")
    parser.add_argument("--video-prompt", default=DEFAULT_VIDEO_PROMPT, help="Prompt used for the video smoke request.")
    parser.add_argument("--image-model", default=None, help="Optional image model override. Falls back to GOOGLE_IMAGE_MODEL.")
    parser.add_argument("--video-model", default=None, help="Optional video model override. Falls back to GOOGLE_VIDEO_MODEL.")
    parser.add_argument("--image-aspect-ratio", default=DEFAULT_IMAGE_ASPECT_RATIO, help="Aspect ratio forwarded to image generation. Default: 1:1.")
    parser.add_argument("--video-aspect-ratio", default=DEFAULT_VIDEO_ASPECT_RATIO, help="Aspect ratio forwarded to video generation. Default: 9:16.")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Overall timeout budget used to derive max polls for video generation.")
    parser.add_argument("--poll-interval-seconds", type=float, default=DEFAULT_POLL_INTERVAL_SECONDS, help="Polling interval used for video operation polling.")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="Optional JSON report path. Default writes to repo tmp_relay_smoke.json.")
    parser.add_argument("--skip-json", action="store_true", help="Do not write JSON report to disk.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client(args)
    report = build_report(args, client)

    if not args.skip_json:
        output_path = Path(args.output_json)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print_summary(report)
    return 0 if report["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
