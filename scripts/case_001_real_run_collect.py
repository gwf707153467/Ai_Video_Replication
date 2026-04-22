from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

APP_CONTAINER = "avr_app"
CASE_ID = "case-001"
DEFAULT_POLL_SECONDS = 5
DEFAULT_MAX_POLLS = 36


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] {message}\n")


def resolve_case_id(payload: dict) -> str:
    compile_options = payload.get("compile_options")
    if isinstance(compile_options, dict):
        proof_case_id = compile_options.get("proof_case_id")
        if isinstance(proof_case_id, str) and proof_case_id.strip():
            return proof_case_id.strip()
    return CASE_ID


def run_container_python_json(script: str, input_payload: dict | None = None) -> dict:
    command = ["docker", "exec", "-i"]
    if input_payload is not None:
        payload_b64 = base64.b64encode(json.dumps(input_payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
        command.extend(["-e", f"CASE001_INPUT_B64={payload_b64}"])
    command.extend([APP_CONTAINER, "python", "-"])
    completed = subprocess.run(command, input=script.encode("utf-8"), capture_output=True)
    stdout = completed.stdout.decode("utf-8", errors="replace").strip()
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    if completed.returncode != 0:
        raise RuntimeError(
            "container python probe failed: "
            f"returncode={completed.returncode}; stderr={stderr or '<empty>'}; stdout={stdout or '<empty>'}"
        )
    if not stdout:
        raise RuntimeError("container python probe returned empty stdout")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"container python probe returned non-json stdout: {stdout}") from exc


def run_container_python_binary(script: str, input_payload: dict) -> bytes:
    command = ["docker", "exec", "-i"]
    payload_b64 = base64.b64encode(json.dumps(input_payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    command.extend(["-e", f"CASE001_INPUT_B64={payload_b64}", APP_CONTAINER, "python", "-"])
    completed = subprocess.run(command, input=script.encode("utf-8"), capture_output=True)
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    if completed.returncode != 0:
        raise RuntimeError(
            "container binary probe failed: "
            f"returncode={completed.returncode}; stderr={stderr or '<empty>'}"
        )
    return completed.stdout


def build_latest_runtime_probe_script() -> str:
    return textwrap.dedent(
        """
        import base64
        import json
        import os
        from uuid import UUID

        from app.db.models.compiled_runtime import CompiledRuntime
        from app.db.session import SessionLocal

        payload = json.loads(base64.b64decode(os.environ["CASE001_INPUT_B64"]).decode("utf-8"))
        project_id = UUID(payload["project_id"])

        db = SessionLocal()
        try:
            runtime = (
                db.query(CompiledRuntime)
                .filter(CompiledRuntime.project_id == project_id)
                .order_by(CompiledRuntime.created_at.desc())
                .first()
            )
            if runtime is None:
                print(json.dumps({"exists": False}, ensure_ascii=False))
            else:
                print(json.dumps({
                    "exists": True,
                    "runtime_id": str(runtime.id),
                    "runtime_version": runtime.runtime_version,
                    "compile_status": runtime.compile_status,
                    "dispatch_status": runtime.dispatch_status,
                    "created_at": runtime.created_at.isoformat() if runtime.created_at else None,
                }, ensure_ascii=False))
        finally:
            db.close()
        """
    ).strip()


def build_compile_dispatch_probe_script() -> str:
    return textwrap.dedent(
        """
        import base64
        import json
        import os
        import urllib.error
        import urllib.request

        payload = json.loads(base64.b64decode(os.environ["CASE001_INPUT_B64"]).decode("utf-8"))
        request = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/compile",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw_body = response.read().decode("utf-8")
                parsed_body = json.loads(raw_body)
                print(json.dumps({
                    "ok": True,
                    "status_code": response.getcode(),
                    "response_json": parsed_body,
                    "raw_body": raw_body,
                }, ensure_ascii=False))
        except urllib.error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace")
            try:
                parsed_body = json.loads(raw_body)
            except json.JSONDecodeError:
                parsed_body = None
            print(json.dumps({
                "ok": False,
                "status_code": exc.code,
                "response_json": parsed_body,
                "raw_body": raw_body,
                "reason": "http_error",
            }, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({
                "ok": False,
                "status_code": None,
                "response_json": None,
                "raw_body": None,
                "reason": f"{type(exc).__name__}:{exc}",
            }, ensure_ascii=False))
        """
    ).strip()


def build_runtime_snapshot_probe_script() -> str:
    return textwrap.dedent(
        """
        import base64
        import json
        import os
        from collections import Counter
        from uuid import UUID

        from app.db.models.asset import Asset
        from app.db.models.compiled_runtime import CompiledRuntime
        from app.db.models.job import Job
        from app.db.session import SessionLocal

        payload = json.loads(base64.b64decode(os.environ["CASE001_INPUT_B64"]).decode("utf-8"))
        project_id = UUID(payload["project_id"])
        runtime_id = UUID(payload["runtime_id"])
        runtime_version = payload["runtime_version"]
        required_asset_types = payload.get("required_asset_types", [
            "generated_image",
            "generated_video",
            "audio",
            "export",
        ])

        def serialize_runtime(runtime):
            return {
                "runtime_id": str(runtime.id),
                "project_id": str(runtime.project_id),
                "runtime_version": runtime.runtime_version,
                "compile_status": runtime.compile_status,
                "dispatch_status": runtime.dispatch_status,
                "dispatch_summary": runtime.dispatch_summary,
                "last_error_code": runtime.last_error_code,
                "last_error_message": runtime.last_error_message,
                "created_at": runtime.created_at.isoformat() if runtime.created_at else None,
                "compile_started_at": runtime.compile_started_at.isoformat() if runtime.compile_started_at else None,
                "compile_finished_at": runtime.compile_finished_at.isoformat() if runtime.compile_finished_at else None,
            }

        def serialize_job(job):
            return {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "attempt_count": job.attempt_count,
                "max_attempts": job.max_attempts,
                "external_task_id": job.external_task_id,
                "error_code": job.error_code,
                "error_message": job.error_message,
                "provider_name": job.provider_name,
                "payload": job.payload,
                "result_payload": job.result_payload,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            }

        def serialize_asset(asset):
            return {
                "asset_id": str(asset.id),
                "asset_type": asset.asset_type,
                "asset_role": asset.asset_role,
                "bucket_name": asset.bucket_name,
                "object_key": asset.object_key,
                "source_filename": asset.source_filename,
                "content_type": asset.content_type,
                "file_size": asset.file_size,
                "asset_metadata": asset.asset_metadata,
                "status": asset.status,
                "notes": asset.notes,
                "created_at": asset.created_at.isoformat() if asset.created_at else None,
            }

        def derive_compile_status(summary, current_status):
            job_count = summary.get("job_count", 0)
            failed_job_count = summary.get("failed_job_count", 0)
            succeeded_job_count = summary.get("succeeded_job_count", 0)
            active_job_count = (
                summary.get("queued_job_count", 0)
                + summary.get("dispatched_job_count", 0)
                + summary.get("running_job_count", 0)
            )
            if job_count == 0:
                return current_status
            if failed_job_count > 0:
                return "failed"
            if succeeded_job_count == job_count:
                return "succeeded"
            if active_job_count > 0:
                return "running"
            return current_status

        def derive_dispatch_status(summary, current_status):
            job_count = summary.get("job_count", 0)
            dispatched_or_beyond = (
                summary.get("dispatched_job_count", 0)
                + summary.get("running_job_count", 0)
                + summary.get("succeeded_job_count", 0)
                + summary.get("failed_job_count", 0)
            )
            if job_count == 0:
                return current_status
            if dispatched_or_beyond == 0:
                return "not_dispatched"
            if dispatched_or_beyond < job_count:
                return "partially_dispatched"
            return "fully_dispatched"

        db = SessionLocal()
        try:
            runtime = (
                db.query(CompiledRuntime)
                .filter(
                    CompiledRuntime.project_id == project_id,
                    CompiledRuntime.id == runtime_id,
                    CompiledRuntime.runtime_version == runtime_version,
                )
                .order_by(CompiledRuntime.created_at.desc())
                .first()
            )
            if runtime is None:
                print(json.dumps({
                    "exists": False,
                    "project_id": str(project_id),
                    "runtime_id": str(runtime_id),
                    "runtime_version": runtime_version,
                }, ensure_ascii=False))
                raise SystemExit(0)

            jobs = (
                db.query(Job)
                .filter(
                    Job.project_id == runtime.project_id,
                    Job.payload["runtime_version"].astext == runtime.runtime_version,
                )
                .order_by(Job.created_at.asc())
                .all()
            )
            counts = Counter(job.status for job in jobs)
            job_summary = {
                "job_count": len(jobs),
                "queued_job_count": counts.get("queued", 0),
                "dispatched_job_count": counts.get("dispatched", 0),
                "running_job_count": counts.get("running", 0),
                "succeeded_job_count": counts.get("succeeded", 0),
                "failed_job_count": counts.get("failed", 0),
            }
            derived_compile_status = derive_compile_status(job_summary, runtime.compile_status)
            derived_dispatch_status = derive_dispatch_status(job_summary, runtime.dispatch_status)

            candidate_assets = (
                db.query(Asset)
                .filter(
                    Asset.project_id == runtime.project_id,
                    Asset.asset_type.in_(required_asset_types),
                )
                .order_by(Asset.created_at.asc())
                .all()
            )
            selected_assets = [
                asset for asset in candidate_assets
                if isinstance(asset.asset_metadata, dict)
                and asset.asset_metadata.get("runtime_version") == runtime.runtime_version
            ]

            print(json.dumps({
                "exists": True,
                "runtime_record": serialize_runtime(runtime),
                "jobs": [serialize_job(job) for job in jobs],
                "job_summary": job_summary,
                "derived_compile_status": derived_compile_status,
                "derived_dispatch_status": derived_dispatch_status,
                "assets": [serialize_asset(asset) for asset in selected_assets],
                "asset_association": {
                    "association_method": "project_id + required_asset_types + asset_metadata.runtime_version",
                    "candidate_asset_count": len(candidate_assets),
                    "selected_asset_count": len(selected_assets),
                    "selected_asset_types": [asset.asset_type for asset in selected_assets],
                    "selected_asset_ids": [str(asset.id) for asset in selected_assets],
                },
            }, ensure_ascii=False))
        finally:
            db.close()
        """
    ).strip()


def build_object_probe_script() -> str:
    return textwrap.dedent(
        """
        import base64
        import json
        import os

        from minio import Minio

        from app.core.config import settings

        payload = json.loads(base64.b64decode(os.environ["CASE001_INPUT_B64"]).decode("utf-8"))
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        objects = []
        for asset in payload.get("assets", []):
            bucket_name = asset.get("bucket_name")
            object_key = asset.get("object_key")
            try:
                stat = client.stat_object(bucket_name, object_key)
                objects.append({
                    "bucket_name": bucket_name,
                    "object_key": object_key,
                    "exists": True,
                    "size": stat.size,
                    "content_type": getattr(stat, "content_type", None),
                })
            except Exception as exc:
                objects.append({
                    "bucket_name": bucket_name,
                    "object_key": object_key,
                    "exists": False,
                    "size": None,
                    "content_type": None,
                    "error": f"{type(exc).__name__}:{exc}",
                })
        print(json.dumps({
            "minio_endpoint": settings.minio_endpoint,
            "objects": objects,
        }, ensure_ascii=False))
        """
    ).strip()


def build_export_fetch_script() -> str:
    return textwrap.dedent(
        """
        import base64
        import json
        import os
        import sys

        from minio import Minio

        from app.core.config import settings

        payload = json.loads(base64.b64decode(os.environ["CASE001_INPUT_B64"]).decode("utf-8"))
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        response = client.get_object(payload["bucket_name"], payload["object_key"])
        try:
            sys.stdout.buffer.write(response.read())
        finally:
            response.close()
            response.release_conn()
        """
    ).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger case-001 compile and collect runtime evidence.")
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--final-output", required=True, type=Path)
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--max-polls", type=int, default=DEFAULT_MAX_POLLS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    args.final_output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.evidence_dir / "run_log.txt"

    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    case_id = resolve_case_id(payload)
    write_json(args.evidence_dir / "compile_request_payload.json", payload)
    append_log(log_path, f"starting {case_id} real-run evidence collection")
    append_log(log_path, f"payload path: {args.payload}")

    latest_before = run_container_python_json(build_latest_runtime_probe_script(), {"project_id": payload["project_id"]})
    latest_before["collected_at"] = utc_now()
    write_json(args.evidence_dir / "pre_compile_latest_runtime.json", latest_before)
    append_log(log_path, f"latest runtime before compile: {json.dumps(latest_before, ensure_ascii=False)}")

    compile_response = run_container_python_json(build_compile_dispatch_probe_script(), payload)
    compile_response["collected_at"] = utc_now()
    write_json(args.evidence_dir / "compile_response.json", compile_response)
    append_log(
        log_path,
        "compile response: " + json.dumps(
            {
                "ok": compile_response.get("ok"),
                "status_code": compile_response.get("status_code"),
                "runtime_id": (compile_response.get("response_json") or {}).get("id"),
                "runtime_version": (compile_response.get("response_json") or {}).get("runtime_version"),
            },
            ensure_ascii=False,
        ),
    )

    runtime_response = compile_response.get("response_json") or {}
    runtime_id = runtime_response.get("id")
    runtime_version = runtime_response.get("runtime_version")

    if not compile_response.get("ok") or not runtime_id or not runtime_version:
        summary = {
            "case_id": case_id,
            "started_at": started_at,
            "finished_at": utc_now(),
            "status": "compile_request_failed_or_incomplete",
            "payload_path": str(args.payload),
            "compile_response_path": str(args.evidence_dir / "compile_response.json"),
            "runtime_id": runtime_id,
            "runtime_version": runtime_version,
            "final_output_path": str(args.final_output),
            "final_output_exists": args.final_output.exists(),
            "note": "This script collects evidence only. It does not upgrade verdict to PROVEN.",
        }
        write_json(args.evidence_dir / "run_summary.json", summary)
        append_log(log_path, "compile did not yield runtime identity; stopping after evidence capture")
        return 1

    poll_history: list[dict] = []
    final_snapshot: dict | None = None
    for index in range(1, args.max_polls + 1):
        snapshot = run_container_python_json(
            build_runtime_snapshot_probe_script(),
            {
                "project_id": payload["project_id"],
                "runtime_id": runtime_id,
                "runtime_version": runtime_version,
            },
        )
        snapshot["poll_index"] = index
        snapshot["collected_at"] = utc_now()
        poll_history.append(snapshot)
        write_json(args.evidence_dir / "runtime_poll_history.json", poll_history)
        append_log(
            log_path,
            "runtime poll: " + json.dumps(
                {
                    "poll_index": index,
                    "derived_compile_status": snapshot.get("derived_compile_status"),
                    "derived_dispatch_status": snapshot.get("derived_dispatch_status"),
                    "job_count": (snapshot.get("job_summary") or {}).get("job_count"),
                    "succeeded_job_count": (snapshot.get("job_summary") or {}).get("succeeded_job_count"),
                    "failed_job_count": (snapshot.get("job_summary") or {}).get("failed_job_count"),
                    "selected_asset_count": len(snapshot.get("assets") or []),
                },
                ensure_ascii=False,
            ),
        )
        if snapshot.get("derived_compile_status") in {"succeeded", "failed"}:
            final_snapshot = snapshot
            break
        if index < args.max_polls:
            time.sleep(args.poll_interval)

    if final_snapshot is None and poll_history:
        final_snapshot = poll_history[-1]

    if final_snapshot is not None:
        write_json(args.evidence_dir / "runtime_snapshot_final.json", final_snapshot)

    object_probe: dict | None = None
    export_pull_report: dict | None = None
    if final_snapshot and final_snapshot.get("assets"):
        object_probe = run_container_python_json(
            build_object_probe_script(),
            {
                "assets": [
                    {
                        "bucket_name": asset.get("bucket_name"),
                        "object_key": asset.get("object_key"),
                    }
                    for asset in final_snapshot.get("assets", [])
                    if asset.get("bucket_name") and asset.get("object_key")
                ]
            },
        )
        object_probe["collected_at"] = utc_now()
        write_json(args.evidence_dir / "object_store_probe.json", object_probe)
        append_log(log_path, f"object probe collected for {len(object_probe.get('objects', []))} objects")

        export_assets = [asset for asset in final_snapshot.get("assets", []) if asset.get("asset_type") == "export"]
        if export_assets:
            export_asset = export_assets[-1]
            try:
                export_bytes = run_container_python_binary(
                    build_export_fetch_script(),
                    {
                        "bucket_name": export_asset["bucket_name"],
                        "object_key": export_asset["object_key"],
                    },
                )
                args.final_output.write_bytes(export_bytes)
                export_pull_report = {
                    "ok": True,
                    "bucket_name": export_asset["bucket_name"],
                    "object_key": export_asset["object_key"],
                    "local_path": str(args.final_output),
                    "byte_count": len(export_bytes),
                    "content_type": export_asset.get("content_type"),
                    "collected_at": utc_now(),
                }
                append_log(log_path, f"export object pulled to {args.final_output} ({len(export_bytes)} bytes)")
            except Exception as exc:
                export_pull_report = {
                    "ok": False,
                    "bucket_name": export_asset.get("bucket_name"),
                    "object_key": export_asset.get("object_key"),
                    "local_path": str(args.final_output),
                    "byte_count": None,
                    "reason": f"{type(exc).__name__}:{exc}",
                    "collected_at": utc_now(),
                }
                append_log(log_path, f"export pull failed: {type(exc).__name__}: {exc}")
        else:
            export_pull_report = {
                "ok": False,
                "reason": "export_asset_missing",
                "local_path": str(args.final_output),
                "collected_at": utc_now(),
            }
            append_log(log_path, "no export asset found in final snapshot")

    if export_pull_report is not None:
        write_json(args.evidence_dir / "export_pull_report.json", export_pull_report)

    summary = {
        "case_id": case_id,
        "started_at": started_at,
        "finished_at": utc_now(),
        "status": "completed_evidence_collection",
        "payload_path": str(args.payload),
        "pre_compile_latest_runtime_path": str(args.evidence_dir / "pre_compile_latest_runtime.json"),
        "compile_response_path": str(args.evidence_dir / "compile_response.json"),
        "runtime_poll_history_path": str(args.evidence_dir / "runtime_poll_history.json"),
        "runtime_snapshot_final_path": str(args.evidence_dir / "runtime_snapshot_final.json"),
        "object_store_probe_path": str(args.evidence_dir / "object_store_probe.json") if object_probe is not None else None,
        "export_pull_report_path": str(args.evidence_dir / "export_pull_report.json") if export_pull_report is not None else None,
        "runtime_id": runtime_id,
        "runtime_version": runtime_version,
        "terminal_compile_status": final_snapshot.get("derived_compile_status") if final_snapshot else None,
        "terminal_dispatch_status": final_snapshot.get("derived_dispatch_status") if final_snapshot else None,
        "final_output_path": str(args.final_output),
        "final_output_exists": args.final_output.exists(),
        "note": "This script collects real-run evidence only. It does not by itself prove playable final MP4 or upgrade verdict to PROVEN.",
    }
    write_json(args.evidence_dir / "run_summary.json", summary)
    append_log(log_path, f"summary: {json.dumps(summary, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
