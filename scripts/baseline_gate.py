#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import textwrap
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.models import Asset, CompiledRuntime, Job, Project  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

GATE_NAME = "production_baseline_gate"
GATE_VERSION = "v1"
DEFAULT_PROJECT_ID = "656ac6b1-ecb8-4f45-9f45-556be5915168"
DEFAULT_COMPILE_REASON = "manual_runtime_validation"
DEFAULT_MODE = "manual_runtime_validation"
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_JSON_NAME = "baseline_gate_verdict.json"
DEFAULT_MD_NAME = "baseline_gate_verdict.md"


@dataclass(frozen=True)
class BaselineExpectation:
    alembic_version: str = "20260330_0004"
    google_image_model: str = "imagen-4.0-fast-generate-001"
    required_services: tuple[str, ...] = (
        "avr_app",
        "avr_worker",
        "avr_postgres",
        "avr_redis",
        "avr_minio",
    )
    required_job_types: tuple[str, ...] = (
        "compile",
        "render_image",
        "render_video",
        "render_voice",
        "merge",
    )
    required_asset_types: tuple[str, ...] = (
        "generated_image",
        "generated_video",
        "audio",
        "export",
    )
    required_health_keys: tuple[str, ...] = (
        "status",
        "app_env",
        "target_market",
        "target_language",
    )
    compose_app_command: str = "command: uvicorn app.main:app --host 0.0.0.0 --port 8000"
    compose_worker_command: str = "command: celery -A app.workers.celery_app worker --loglevel=INFO"
    forbidden_bind: str = "- .:/workspace"
    expected_runtime_buckets: dict[str, str] = field(
        default_factory=lambda: {
            "minio_bucket_reference": "reference-assets",
            "minio_bucket_generated_images": "generated-images",
            "minio_bucket_generated_videos": "generated-videos",
            "minio_bucket_audio": "audio-assets",
            "minio_bucket_exports": "exports",
            "minio_bucket_runtime": "runtime-packets",
        }
    )


EXPECTATION = BaselineExpectation()


@dataclass
class GateContext:
    repo_root: str
    project_id: str
    compile_reason: str
    mode: str
    timeout_seconds: int
    poll_interval_seconds: int
    output_json: Path | None
    output_md: Path | None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaselineGateError(Exception):
    pass


class BaselineDriftError(BaselineGateError):
    pass


class BaselineFailError(BaselineGateError):
    pass


class BaselineInconclusiveError(BaselineGateError):
    pass


class VerdictBuilder:
    def __init__(self, ctx: GateContext) -> None:
        self.ctx = ctx
        self.verdict: dict[str, Any] = {
            "gate_name": GATE_NAME,
            "gate_version": GATE_VERSION,
            "executed_at": None,
            "repo_root": ctx.repo_root,
            "project_id": ctx.project_id,
            "runtime_id": None,
            "runtime_version": None,
            "verdict": "INCONCLUSIVE",
            "summary": "Gate not executed yet.",
            "baseline_freeze": {
                "status": "pending",
                "checks": {},
            },
            "compile_dispatch": {
                "status": "pending",
                "compile_validate_passed": False,
                "compile_request_passed": False,
                "job_count": 0,
                "job_types": [],
                "initial_dispatch_status": None,
            },
            "runtime_completion": {
                "status": "pending",
                "compile_status": None,
                "dispatch_status": None,
                "stored_compile_status": None,
                "stored_dispatch_status": None,
                "job_count": 0,
                "queued_job_count": 0,
                "dispatched_job_count": 0,
                "running_job_count": 0,
                "succeeded_job_count": 0,
                "failed_job_count": 0,
                "last_error_code": None,
            },
            "asset_materialization": {
                "status": "pending",
                "required_asset_types": list(EXPECTATION.required_asset_types),
                "materialized_asset_count": 0,
                "assets": [],
            },
            "object_store": {
                "status": "pending",
                "probe_method": "app_container_minio_python_probe",
                "checked_object_count": 0,
                "existing_object_count": 0,
                "objects": [],
            },
            "evidence": {
                "health_response": None,
                "compile_validate_response": None,
                "compile_dispatch_response": None,
                "alembic_version": None,
                "settings_snapshot": {},
                "runtime_record": None,
                "runtime_dispatch_summary": {},
                "runtime_asset_association": {},
                "jobs": [],
                "assets": [],
                "stage_timings": {},
                "compose_snapshot": {},
                "running_services": {},
                "runtime_poll_snapshot": {},
            },
            "warnings": [],
            "drifts": [],
            "failures": [],
        }

    def set_runtime_identity(self, runtime: CompiledRuntime | None) -> None:
        if runtime is None:
            return
        self.verdict["runtime_id"] = str(runtime.id)
        self.verdict["runtime_version"] = runtime.runtime_version

    def set_runtime_identity_from_values(self, runtime_id: str | None, runtime_version: str | None) -> None:
        if runtime_id:
            self.verdict["runtime_id"] = runtime_id
        if runtime_version:
            self.verdict["runtime_version"] = runtime_version

    def add_warning(self, message: str) -> None:
        self.verdict["warnings"].append(message)

    def add_drift(self, message: str) -> None:
        self.verdict["drifts"].append(message)

    def add_failure(self, message: str) -> None:
        self.verdict["failures"].append(message)

    def set_stage_timing(self, stage_name: str, started: float, finished: float) -> None:
        self.verdict["evidence"]["stage_timings"][stage_name] = {
            "started_monotonic": started,
            "finished_monotonic": finished,
            "duration_seconds": round(finished - started, 3),
        }

    def finalize(self, verdict: str, summary: str) -> dict[str, Any]:
        self.verdict["executed_at"] = datetime.now(timezone.utc).isoformat()
        self.verdict["verdict"] = verdict
        self.verdict["summary"] = summary
        return self.verdict


class BaselineGate:
    def __init__(self, ctx: GateContext) -> None:
        self.ctx = ctx
        self.expectation = EXPECTATION
        self.verdict = VerdictBuilder(ctx)

    def run(self) -> dict[str, Any]:
        try:
            self._run_stage("baseline_freeze", self.stage_0_baseline_freeze_precheck)
            self._run_stage("health_probe", self.stage_1_health_probe)
            self._run_stage("compile_validate", self.stage_2_compile_validate)
            compile_result = self._run_stage("compile_dispatch", self.stage_3_compile_dispatch_probe)
            runtime = self._run_stage("runtime_polling", self.stage_4_runtime_polling, compile_result)
            db_evidence = self._run_stage("db_evidence", self.stage_5_db_evidence_collection, runtime)
            self._run_stage("object_store", self.stage_6_object_store_probe, db_evidence)
            summary = self._run_stage("verdict_render", self.stage_7_verdict_render)
            return self.verdict.finalize("PASS", summary)
        except BaselineDriftError as exc:
            return self.verdict.finalize("DRIFT", str(exc))
        except BaselineFailError as exc:
            return self.verdict.finalize("FAIL", str(exc))
        except BaselineInconclusiveError as exc:
            return self.verdict.finalize("INCONCLUSIVE", str(exc))
        except Exception as exc:  # pragma: no cover - defensive guardrail
            self.verdict.add_failure(f"unexpected_exception:{type(exc).__name__}:{exc}")
            return self.verdict.finalize("INCONCLUSIVE", f"Unexpected gate exception: {exc}")

    def _run_stage(self, stage_name: str, func, *args):
        started = time.monotonic()
        result = func(*args)
        finished = time.monotonic()
        self.verdict.set_stage_timing(stage_name, started, finished)
        return result

    def stage_0_baseline_freeze_precheck(self) -> None:
        checks = {
            "repo_root_correct": Path(self.ctx.repo_root).resolve() == REPO_ROOT,
            "docker_compose_available": False,
            "compose_baseline_locked": False,
            "services_running": False,
            "migration_at_head": False,
            "google_image_model_locked": False,
            "runtime_buckets_locked": False,
            "smoke_project_exists": False,
        }

        docker_compose_snapshot = self._check_docker_compose_available()
        compose_snapshot = self._inspect_compose_freeze()
        running_services_snapshot = self._list_running_services()
        alembic_version = self._fetch_alembic_version()
        settings_snapshot = self._load_app_container_settings_snapshot()

        self.verdict.verdict["evidence"]["compose_snapshot"] = {
            **compose_snapshot,
            "docker_compose": docker_compose_snapshot,
        }
        self.verdict.verdict["evidence"]["running_services"] = running_services_snapshot
        self.verdict.verdict["evidence"]["alembic_version"] = alembic_version
        self.verdict.verdict["evidence"]["settings_snapshot"] = settings_snapshot

        checks["docker_compose_available"] = docker_compose_snapshot.get("available", False)
        if not checks["repo_root_correct"]:
            self.verdict.add_drift(f"repo_root_mismatch:{self.ctx.repo_root}")
        if not checks["docker_compose_available"]:
            self.verdict.add_drift("docker-compose command unavailable")

        checks["compose_baseline_locked"] = compose_snapshot.get("all_locked", False)
        if not checks["compose_baseline_locked"]:
            self.verdict.add_drift("docker_compose_freeze_mismatch")

        running_names = set(running_services_snapshot.get("running_names", []))
        checks["services_running"] = all(name in running_names for name in self.expectation.required_services)
        if not checks["services_running"]:
            self.verdict.add_drift(f"services_running_mismatch:{sorted(running_names)}")

        checks["migration_at_head"] = alembic_version == self.expectation.alembic_version
        if not checks["migration_at_head"]:
            self.verdict.add_drift(f"unexpected_alembic_version:{alembic_version}")

        checks["google_image_model_locked"] = (
            settings_snapshot.get("google_image_model") == self.expectation.google_image_model
        )
        if not checks["google_image_model_locked"]:
            self.verdict.add_drift(
                f"unexpected_google_image_model:{settings_snapshot.get('google_image_model')}"
            )

        actual_runtime_buckets = {
            key: settings_snapshot.get(key)
            for key in self.expectation.expected_runtime_buckets
        }
        checks["runtime_buckets_locked"] = actual_runtime_buckets == self.expectation.expected_runtime_buckets
        if not checks["runtime_buckets_locked"]:
            self.verdict.add_drift(
                f"unexpected_runtime_buckets:{json.dumps(actual_runtime_buckets, ensure_ascii=False, sort_keys=True)}"
            )

        with SessionLocal() as db:
            project = db.get(Project, UUID(self.ctx.project_id))
            checks["smoke_project_exists"] = project is not None

        if not checks["smoke_project_exists"]:
            self.verdict.add_drift(f"smoke_project_missing:{self.ctx.project_id}")

        self.verdict.verdict["baseline_freeze"] = {
            "status": "pass" if all(checks.values()) else "drift",
            "checks": checks,
            "expected_runtime_buckets": self.expectation.expected_runtime_buckets,
            "actual_runtime_buckets": actual_runtime_buckets,
        }
        if not all(checks.values()):
            raise BaselineDriftError("Baseline freeze drifted: one or more prechecks failed.")

    def stage_1_health_probe(self) -> dict[str, Any]:
        probe_result = self._run_app_python_probe(self._build_health_probe_script())
        http_status = probe_result.get("http_status")
        payload = probe_result.get("payload")

        if http_status != 200 or not isinstance(payload, dict):
            self.verdict.add_failure(f"health_probe_unexpected_response:{probe_result}")
            raise BaselineFailError("Health probe failed: app container probe did not return HTTP 200 JSON.")

        missing_keys = sorted(set(self.expectation.required_health_keys) - set(payload.keys()))
        if missing_keys:
            self.verdict.add_failure(f"health_probe_missing_required_keys:{missing_keys}")
            raise BaselineFailError("Health probe failed: response missing required keys.")

        self.verdict.verdict["evidence"]["health_response"] = payload
        return probe_result

    def stage_2_compile_validate(self) -> dict[str, Any]:
        probe_result = self._run_app_python_probe(
            self._build_compile_validate_probe_script(self.ctx.project_id)
        )
        http_status = probe_result.get("http_status")
        payload = probe_result.get("payload")
        self.verdict.verdict["evidence"]["compile_validate_response"] = probe_result

        if http_status != 200 or not isinstance(payload, dict):
            self.verdict.add_failure(f"compile_validate_unexpected_response:{probe_result}")
            raise BaselineInconclusiveError(
                "Compile validate probe inconclusive: app container probe did not return expected JSON."
            )

        warnings = payload.get("warnings", []) or []
        errors = payload.get("errors", []) or []
        for warning in warnings:
            self.verdict.add_warning(f"compile_validate_warning:{warning}")
        if not payload.get("is_valid") or errors:
            for error in errors:
                self.verdict.add_failure(f"compile_validate_error:{error}")
            self.verdict.verdict["compile_dispatch"]["status"] = "fail"
            raise BaselineFailError("Compile validate failed: project is not valid.")

        self.verdict.verdict["compile_dispatch"]["compile_validate_passed"] = True
        return probe_result

    def stage_3_compile_dispatch_probe(self) -> dict[str, Any]:
        with SessionLocal() as db:
            previous_runtime = self._get_latest_runtime_for_project(db)

        request_payload = self._build_compile_dispatch_payload()
        probe_result = self._run_app_python_probe(
            self._build_compile_dispatch_probe_script(request_payload),
            input_payload=request_payload,
        )
        http_status = probe_result.get("http_status")
        payload = probe_result.get("payload")
        self.verdict.verdict["evidence"]["compile_dispatch_response"] = probe_result

        if http_status not in {200, 201} or not isinstance(payload, dict):
            self.verdict.add_failure(f"compile_dispatch_unexpected_response:{probe_result}")
            raise BaselineFailError("Compile dispatch failed: app container probe did not return expected JSON.")

        runtime_id = payload.get("id")
        runtime_version = payload.get("runtime_version")
        dispatch_summary = payload.get("dispatch_summary") or {}
        if not runtime_id or not runtime_version or not isinstance(dispatch_summary, dict):
            self.verdict.add_failure("compile_dispatch_missing_runtime_identity_or_summary")
            raise BaselineFailError("Compile dispatch failed: missing runtime identity or dispatch summary.")

        if previous_runtime is not None:
            if str(previous_runtime.id) == str(runtime_id):
                self.verdict.add_failure(f"compile_dispatch_runtime_id_not_new:{runtime_id}")
                raise BaselineFailError("Compile dispatch failed: runtime_id was not newly issued.")
            if previous_runtime.runtime_version == runtime_version:
                self.verdict.add_failure(f"compile_dispatch_runtime_version_not_new:{runtime_version}")
                raise BaselineFailError("Compile dispatch failed: runtime_version was not newly issued.")

        observed_job_types = sorted(
            {
                item.get("job_type")
                for item in dispatch_summary.get("jobs", [])
                if isinstance(item, dict) and item.get("job_type")
            }
        )
        self.verdict.set_runtime_identity_from_values(runtime_id, runtime_version)
        self.verdict.verdict["compile_dispatch"].update(
            {
                "status": "pass",
                "compile_request_passed": True,
                "job_count": dispatch_summary.get("job_count", 0),
                "job_types": observed_job_types,
                "initial_dispatch_status": payload.get("dispatch_status"),
            }
        )
        self.verdict.verdict["evidence"]["runtime_dispatch_summary"] = dispatch_summary
        return {
            "runtime_id": runtime_id,
            "runtime_version": runtime_version,
            "compile_response": payload,
        }

    def stage_4_runtime_polling(self, compile_result: dict[str, Any]) -> CompiledRuntime:
        deadline = time.monotonic() + self.ctx.timeout_seconds
        runtime: CompiledRuntime | None = None
        latest_snapshot: dict[str, Any] | None = None

        while time.monotonic() <= deadline:
            with SessionLocal() as db:
                runtime = self._get_runtime_by_identity(
                    db,
                    runtime_id=compile_result["runtime_id"],
                    runtime_version=compile_result["runtime_version"],
                )
                if runtime is None:
                    latest_snapshot = None
                else:
                    latest_snapshot = self._collect_runtime_poll_snapshot(db, runtime)
                    self.verdict.verdict["evidence"]["runtime_poll_snapshot"] = latest_snapshot
                    self.verdict.verdict["evidence"]["runtime_dispatch_summary"] = latest_snapshot["job_summary"]
                    self.verdict.verdict["runtime_completion"].update(
                        {
                            "compile_status": latest_snapshot["derived_compile_status"],
                            "dispatch_status": latest_snapshot["derived_dispatch_status"],
                            "stored_compile_status": latest_snapshot["stored_compile_status"],
                            "stored_dispatch_status": latest_snapshot["stored_dispatch_status"],
                            "job_count": latest_snapshot["job_count"],
                            "queued_job_count": latest_snapshot["queued_job_count"],
                            "dispatched_job_count": latest_snapshot["dispatched_job_count"],
                            "running_job_count": latest_snapshot["running_job_count"],
                            "succeeded_job_count": latest_snapshot["succeeded_job_count"],
                            "failed_job_count": latest_snapshot["failed_job_count"],
                            "last_error_code": latest_snapshot["last_error_code"],
                        }
                    )
                    if (
                        latest_snapshot["dispatched_job_count"] == 0
                        and latest_snapshot["derived_compile_status"] == "succeeded"
                    ):
                        self.verdict.add_warning(
                            "terminal_runtime_dispatched_job_count_zero_is_expected_when_all_jobs_have_advanced_beyond_dispatch"
                        )
                    if latest_snapshot["derived_compile_status"] in {"succeeded", "failed"}:
                        break
            time.sleep(self.ctx.poll_interval_seconds)

        if runtime is None:
            self.verdict.add_failure("runtime_polling_never_observed_runtime")
            raise BaselineInconclusiveError("Runtime polling inconclusive: runtime was never observed.")
        if latest_snapshot is None:
            self.verdict.add_failure("runtime_polling_missing_snapshot")
            raise BaselineInconclusiveError("Runtime polling inconclusive: runtime snapshot was not collected.")

        if latest_snapshot["stored_compile_status"] != latest_snapshot["derived_compile_status"]:
            self.verdict.add_warning(
                "runtime_row_compile_status_differs_from_observed_job_summary"
            )
        if latest_snapshot["stored_dispatch_status"] != latest_snapshot["derived_dispatch_status"]:
            self.verdict.add_warning(
                "runtime_row_dispatch_status_differs_from_observed_job_summary"
            )

        if latest_snapshot["derived_compile_status"] != "succeeded":
            self.verdict.verdict["runtime_completion"]["status"] = "fail"
            self.verdict.add_failure(
                f"runtime_terminal_status:{latest_snapshot['derived_compile_status']}"
            )
            raise BaselineFailError(
                f"Runtime completion failed: terminal status is {latest_snapshot['derived_compile_status']}."
            )

        if latest_snapshot["derived_dispatch_status"] != "fully_dispatched":
            self.verdict.verdict["runtime_completion"]["status"] = "fail"
            self.verdict.add_failure(
                f"runtime_dispatch_status:{latest_snapshot['derived_dispatch_status']}"
            )
            raise BaselineFailError(
                "Runtime completion failed: observed dispatch status is not fully_dispatched."
            )

        self.verdict.verdict["runtime_completion"]["status"] = "pass"
        return runtime

    def stage_5_db_evidence_collection(self, runtime: CompiledRuntime) -> dict[str, Any]:
        failure_count_before = len(self.verdict.verdict["failures"])
        with SessionLocal() as db:
            runtime = self._get_runtime_by_identity(
                db,
                runtime_id=str(runtime.id),
                runtime_version=runtime.runtime_version,
            )
            if runtime is None:
                self.verdict.add_failure("runtime_missing_during_db_evidence_collection")
                raise BaselineInconclusiveError(
                    "DB evidence inconclusive: runtime missing at collection stage."
                )

            jobs = (
                db.query(Job)
                .filter(
                    Job.project_id == runtime.project_id,
                    Job.payload["runtime_version"].astext == runtime.runtime_version,
                )
                .order_by(Job.created_at.asc())
                .all()
            )
            assets, asset_association = self._collect_runtime_assets(db, runtime)

            job_entries = [self._serialize_job(job) for job in jobs]
            asset_entries = [self._serialize_asset(asset) for asset in assets]
            self.verdict.set_runtime_identity(runtime)
            self.verdict.verdict["evidence"]["runtime_record"] = self._serialize_runtime(runtime)
            self.verdict.verdict["evidence"]["jobs"] = job_entries
            self.verdict.verdict["evidence"]["assets"] = asset_entries
            self.verdict.verdict["evidence"]["runtime_asset_association"] = asset_association

            observed_job_types = [entry["job_type"] for entry in job_entries]
            missing_job_types = [
                job_type
                for job_type in self.expectation.required_job_types
                if job_type not in observed_job_types
            ]
            non_succeeded_jobs = [entry for entry in job_entries if entry["status"] != "succeeded"]
            missing_external_task_id = [
                entry["job_id"] for entry in job_entries if not entry.get("external_task_id")
            ]

            if len(job_entries) != len(self.expectation.required_job_types):
                self.verdict.add_failure(f"unexpected_job_count:{len(job_entries)}")
            if missing_job_types:
                self.verdict.add_failure(f"missing_job_types:{missing_job_types}")
            if non_succeeded_jobs:
                self.verdict.add_failure(
                    f"non_succeeded_jobs:{[entry['job_id'] for entry in non_succeeded_jobs]}"
                )
            if missing_external_task_id:
                self.verdict.add_failure(
                    f"missing_external_task_id:{missing_external_task_id}"
                )

            observed_asset_types = [entry["asset_type"] for entry in asset_entries]
            missing_asset_types = [
                asset_type
                for asset_type in self.expectation.required_asset_types
                if asset_type not in observed_asset_types
            ]
            materialized_assets = [entry for entry in asset_entries if entry["status"] == "materialized"]
            non_materialized_assets = [
                entry["asset_id"] for entry in asset_entries if entry["status"] != "materialized"
            ]
            duplicate_asset_types = {
                asset_type: count
                for asset_type, count in Counter(observed_asset_types).items()
                if count > 1
            }

            self.verdict.verdict["compile_dispatch"].update(
                {
                    "job_count": len(job_entries),
                    "job_types": observed_job_types,
                }
            )
            self.verdict.verdict["asset_materialization"].update(
                {
                    "materialized_asset_count": len(materialized_assets),
                    "assets": asset_entries,
                }
            )

            if asset_association.get("runtime_version_filter_status") != "tentative_confirmed_by_data":
                self.verdict.add_warning(
                    "asset_runtime_version_association_is_tentative_and_not_confirmed_by_data"
                )
            if missing_asset_types:
                self.verdict.add_failure(f"missing_asset_types:{missing_asset_types}")
            if non_materialized_assets:
                self.verdict.add_failure(f"non_materialized_assets:{non_materialized_assets}")
            if len(materialized_assets) < len(self.expectation.required_asset_types):
                self.verdict.add_failure(
                    f"unexpected_materialized_asset_count:{len(materialized_assets)}"
                )
            if duplicate_asset_types:
                self.verdict.add_warning(f"duplicate_asset_types:{duplicate_asset_types}")

            if len(self.verdict.verdict["failures"]) > failure_count_before:
                self.verdict.verdict["asset_materialization"]["status"] = "fail"
                raise BaselineFailError(
                    "DB evidence collection failed: runtime jobs or assets do not meet baseline gate."
                )

            self.verdict.verdict["asset_materialization"]["status"] = "pass"
            return {
                "runtime": runtime,
                "jobs": jobs,
                "assets": assets,
                "asset_entries": asset_entries,
                "job_entries": job_entries,
            }

    def stage_6_object_store_probe(self, db_evidence: dict[str, Any]) -> list[dict[str, Any]]:
        target_assets = db_evidence["asset_entries"]
        probe_result = self._run_app_python_probe(
            self._build_object_probe_script(target_assets),
            input_payload={"assets": target_assets},
        )
        object_entries = probe_result.get("objects")
        if not isinstance(object_entries, list):
            self.verdict.add_failure(f"object_probe_unexpected_response:{probe_result}")
            raise BaselineInconclusiveError(
                "Object store probe inconclusive: app container probe did not return object list."
            )

        existing_count = sum(1 for item in object_entries if item.get("exists") is True)
        self.verdict.verdict["object_store"].update(
            {
                "status": "pass" if existing_count == len(object_entries) else "fail",
                "checked_object_count": len(object_entries),
                "existing_object_count": existing_count,
                "objects": object_entries,
            }
        )

        missing_objects = [
            item for item in object_entries if not item.get("exists")
        ]
        if missing_objects:
            for item in missing_objects:
                self.verdict.add_failure(
                    "object_probe_failed:"
                    f"{item.get('bucket_name')}:{item.get('object_key')}:{item.get('error')}"
                )
            raise BaselineFailError(
                "Object store probe failed: one or more DB-backed target objects do not exist."
            )
        return object_entries

    def stage_7_verdict_render(self) -> str:
        layer_statuses = {
            "baseline_freeze": self.verdict.verdict["baseline_freeze"].get("status"),
            "compile_dispatch": self.verdict.verdict["compile_dispatch"].get("status"),
            "runtime_completion": self.verdict.verdict["runtime_completion"].get("status"),
            "asset_materialization": self.verdict.verdict["asset_materialization"].get("status"),
            "object_store": self.verdict.verdict["object_store"].get("status"),
        }
        pending_layers = [name for name, status in layer_statuses.items() if status in {None, "pending"}]
        if pending_layers:
            raise BaselineInconclusiveError(
                f"Verdict render inconclusive: pending layers remain {pending_layers}."
            )
        if self.verdict.verdict["runtime_id"] is None or self.verdict.verdict["runtime_version"] is None:
            raise BaselineInconclusiveError(
                "Verdict render inconclusive: runtime identity is missing."
            )
        if self.verdict.verdict["drifts"] or layer_statuses["baseline_freeze"] == "drift":
            raise BaselineDriftError("Baseline freeze drift detected during verdict rendering.")
        fail_layers = [name for name, status in layer_statuses.items() if status == "fail"]
        if self.verdict.verdict["failures"] or fail_layers:
            raise BaselineFailError(
                f"Baseline gate failed: fail layers={fail_layers or ['unknown']}"
            )
        return (
            "Baseline gate passed: frozen sandbox baseline remained repeatable across "
            "baseline freeze, compile dispatch, runtime completion, asset materialization, and object store evidence."
        )

    def _check_docker_compose_available(self) -> dict[str, Any]:
        result = subprocess.run(
            ["docker-compose", "version"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "available": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    def _inspect_compose_freeze(self) -> dict[str, Any]:
        compose_path = REPO_ROOT / "docker-compose.yml"
        compose_text = compose_path.read_text(encoding="utf-8")
        app_block = self._extract_service_block(compose_text, "app")
        worker_block = self._extract_service_block(compose_text, "worker")

        app_has_forbidden_bind = self.expectation.forbidden_bind in "\n".join(app_block)
        worker_has_forbidden_bind = self.expectation.forbidden_bind in "\n".join(worker_block)
        app_command_locked = self.expectation.compose_app_command in "\n".join(app_block)
        worker_command_locked = self.expectation.compose_worker_command in "\n".join(worker_block)

        return {
            "compose_path": str(compose_path),
            "app": {
                "command_locked": app_command_locked,
                "forbidden_bind_present": app_has_forbidden_bind,
                "block_excerpt": app_block,
            },
            "worker": {
                "command_locked": worker_command_locked,
                "forbidden_bind_present": worker_has_forbidden_bind,
                "block_excerpt": worker_block,
            },
            "all_locked": (
                app_command_locked
                and worker_command_locked
                and not app_has_forbidden_bind
                and not worker_has_forbidden_bind
            ),
        }

    def _extract_service_block(self, compose_text: str, service_name: str) -> list[str]:
        lines = compose_text.splitlines()
        start_marker = f"  {service_name}:"
        block: list[str] = []
        collecting = False
        for line in lines:
            if line == start_marker:
                collecting = True
            if collecting:
                if line.startswith("  ") and not line.startswith("    ") and line != start_marker and line.endswith(":"):
                    break
                block.append(line)
        return block

    def _list_running_services(self) -> dict[str, Any]:
        result = subprocess.run(
            ["docker-compose", "ps"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        snapshot: dict[str, Any] = {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "names": [],
            "running_names": [],
        }
        if result.returncode != 0:
            self.verdict.add_drift(f"docker_compose_ps_failed:{result.stderr.strip()}")
            return snapshot

        names: list[str] = []
        running_names: list[str] = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("Name") or stripped.startswith("---"):
                continue
            name = stripped.split()[0]
            names.append(name)
            if " Up " in f" {stripped} " or stripped.endswith(" Up"):
                running_names.append(name)
        snapshot["names"] = sorted(set(names))
        snapshot["running_names"] = sorted(set(running_names))
        return snapshot

    def _fetch_alembic_version(self) -> str | None:
        with SessionLocal() as db:
            row = db.execute(text("select version_num from alembic_version limit 1")).fetchone()
            return row[0] if row else None

    def _load_app_container_settings_snapshot(self) -> dict[str, Any]:
        return self._run_app_python_probe(self._build_settings_snapshot_probe_script())

    def _run_app_python_probe(
        self,
        script: str,
        input_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload_b64 = ""
        if input_payload is not None:
            payload_b64 = base64.b64encode(
                json.dumps(input_payload, ensure_ascii=False).encode("utf-8")
            ).decode("ascii")

        inner_script = textwrap.dedent(script).strip()
        wrapped_lines = [
            "import base64",
            "import json",
            "import os",
            "",
            '_raw_input_b64 = os.environ.get("BASELINE_GATE_INPUT_B64", "")',
            "INPUT_PAYLOAD = None",
            "if _raw_input_b64:",
            '    INPUT_PAYLOAD = json.loads(base64.b64decode(_raw_input_b64).decode("utf-8"))',
        ]
        if inner_script:
            wrapped_lines.extend(["", inner_script])
        wrapped_script = "\n".join(wrapped_lines) + "\n"

        command = ["docker", "exec", "-i"]
        if payload_b64:
            command.extend(["-e", f"BASELINE_GATE_INPUT_B64={payload_b64}"])
        command.extend(["avr_app", "python", "-"])

        result = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            input=wrapped_script,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise BaselineInconclusiveError(
                "App container probe failed: "
                f"returncode={result.returncode}, stderr={result.stderr.strip()}"
            )

        stdout = result.stdout
        if not stdout.strip():
            raise BaselineInconclusiveError("App container probe failed: stdout was empty.")

        payload = self._extract_probe_json_from_stdout(stdout)
        if not isinstance(payload, dict):
            raise BaselineInconclusiveError(
                f"App container probe failed: expected JSON object, got {type(payload).__name__}."
            )
        return payload

    def _extract_probe_json_from_stdout(self, stdout: str) -> Any:
        candidates: list[str] = []
        stripped_stdout = stdout.strip()
        if stripped_stdout:
            candidates.append(stripped_stdout)
        candidates.extend(line.strip() for line in stdout.splitlines() if line.strip())

        seen: set[str] = set()
        for candidate in reversed(candidates):
            if candidate in seen:
                continue
            seen.add(candidate)
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        raise BaselineInconclusiveError(
            "App container probe failed: could not recover a JSON object payload from stdout. "
            f"stdout={stripped_stdout}"
        )

    def _build_settings_snapshot_probe_script(self) -> str:
        return textwrap.dedent(
            """
            from app.core.config import settings

            print(json.dumps({
                "app_env": settings.app_env,
                "google_image_model": settings.google_image_model,
                "minio_endpoint": settings.minio_endpoint,
                "minio_secure": settings.minio_secure,
                "minio_bucket_reference": settings.minio_bucket_reference,
                "minio_bucket_generated_images": settings.minio_bucket_generated_images,
                "minio_bucket_generated_videos": settings.minio_bucket_generated_videos,
                "minio_bucket_audio": settings.minio_bucket_audio,
                "minio_bucket_exports": settings.minio_bucket_exports,
                "minio_bucket_runtime": settings.minio_bucket_runtime,
            }, ensure_ascii=False))
            """
        ).strip()

    def _build_health_probe_script(self) -> str:
        return textwrap.dedent(
            """
            import urllib.request

            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=30) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body)
                print(json.dumps({
                    "http_status": response.status,
                    "payload": payload,
                }, ensure_ascii=False))
            """
        ).strip()

    def _build_compile_validate_probe_script(self, project_id: str) -> str:
        return textwrap.dedent(
            f"""
            import urllib.request

            with urllib.request.urlopen(
                "http://127.0.0.1:8000/api/v1/compile/validate/{project_id}",
                timeout=30,
            ) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body)
                print(json.dumps({{
                    "http_status": response.status,
                    "payload": payload,
                }}, ensure_ascii=False))
            """
        ).strip()

    def _build_compile_dispatch_payload(self) -> dict[str, Any]:
        return {
            "project_id": self.ctx.project_id,
            "compile_reason": self.ctx.compile_reason,
            "compile_options": {"mode": self.ctx.mode},
            "auto_version": True,
            "dispatch_jobs": True,
        }

    def _build_compile_dispatch_probe_script(self, payload: dict[str, Any]) -> str:
        del payload  # payload is passed through INPUT_PAYLOAD by the runner.
        return textwrap.dedent(
            """
            import urllib.request

            request = urllib.request.Request(
                "http://127.0.0.1:8000/api/v1/compile",
                data=json.dumps(INPUT_PAYLOAD).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body)
                print(json.dumps({
                    "http_status": response.status,
                    "payload": payload,
                }, ensure_ascii=False))
            """
        ).strip()

    def _build_object_probe_script(self, assets: list[dict[str, Any]]) -> str:
        del assets  # assets are passed through INPUT_PAYLOAD by the runner.
        return textwrap.dedent(
            """
            from minio import Minio
            from app.core.config import settings

            client = Minio(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )

            object_entries = []
            for asset in INPUT_PAYLOAD.get("assets", []):
                bucket_name = asset.get("bucket_name")
                object_key = asset.get("object_key")
                try:
                    stat = client.stat_object(bucket_name, object_key)
                    object_entries.append({
                        "bucket_name": bucket_name,
                        "object_key": object_key,
                        "exists": True,
                        "size": stat.size,
                        "content_type": getattr(stat, "content_type", None),
                    })
                except Exception as exc:
                    object_entries.append({
                        "bucket_name": bucket_name,
                        "object_key": object_key,
                        "exists": False,
                        "size": None,
                        "content_type": None,
                        "error": f"{type(exc).__name__}:{exc}",
                    })

            print(json.dumps({
                "minio_endpoint": settings.minio_endpoint,
                "objects": object_entries,
            }, ensure_ascii=False))
            """
        ).strip()

    def _get_latest_runtime_for_project(self, db: Session) -> CompiledRuntime | None:
        return (
            db.query(CompiledRuntime)
            .filter(CompiledRuntime.project_id == UUID(self.ctx.project_id))
            .order_by(CompiledRuntime.created_at.desc())
            .first()
        )

    def _get_runtime_by_identity(
        self,
        db: Session,
        runtime_id: str,
        runtime_version: str,
    ) -> CompiledRuntime | None:
        return (
            db.query(CompiledRuntime)
            .filter(
                CompiledRuntime.project_id == UUID(self.ctx.project_id),
                CompiledRuntime.id == UUID(runtime_id),
                CompiledRuntime.runtime_version == runtime_version,
            )
            .order_by(CompiledRuntime.created_at.desc())
            .first()
        )

    def _collect_runtime_poll_snapshot(self, db: Session, runtime: CompiledRuntime) -> dict[str, Any]:
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
        summary = {
            "runtime_version": runtime.runtime_version,
            "job_count": len(jobs),
            "queued_job_count": counts.get("queued", 0),
            "dispatched_job_count": counts.get("dispatched", 0),
            "running_job_count": counts.get("running", 0),
            "succeeded_job_count": counts.get("succeeded", 0),
            "failed_job_count": counts.get("failed", 0),
            "jobs": [
                {
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                    "status": job.status,
                    "external_task_id": job.external_task_id,
                    "error_code": job.error_code,
                }
                for job in jobs
            ],
        }
        return {
            "runtime_id": str(runtime.id),
            "runtime_version": runtime.runtime_version,
            "stored_compile_status": runtime.compile_status,
            "stored_dispatch_status": runtime.dispatch_status,
            "derived_compile_status": self._derive_compile_status(summary, runtime.compile_status),
            "derived_dispatch_status": self._derive_dispatch_status(summary, runtime.dispatch_status),
            "job_count": summary["job_count"],
            "queued_job_count": summary["queued_job_count"],
            "dispatched_job_count": summary["dispatched_job_count"],
            "running_job_count": summary["running_job_count"],
            "succeeded_job_count": summary["succeeded_job_count"],
            "failed_job_count": summary["failed_job_count"],
            "last_error_code": runtime.last_error_code,
            "last_error_message": runtime.last_error_message,
            "job_summary": summary,
        }

    def _derive_compile_status(self, summary: dict[str, Any], current_status: str | None) -> str | None:
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

    def _derive_dispatch_status(self, summary: dict[str, Any], current_status: str | None) -> str | None:
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

    def _collect_runtime_assets(
        self,
        db: Session,
        runtime: CompiledRuntime,
    ) -> tuple[list[Asset], dict[str, Any]]:
        candidates = (
            db.query(Asset)
            .filter(
                Asset.project_id == runtime.project_id,
                Asset.asset_type.in_(self.expectation.required_asset_types),
            )
            .order_by(Asset.created_at.asc())
            .all()
        )
        selected = [
            asset
            for asset in candidates
            if isinstance(asset.asset_metadata, dict)
            and asset.asset_metadata.get("runtime_version") == runtime.runtime_version
        ]
        selected_metadata = [asset.asset_metadata for asset in selected if isinstance(asset.asset_metadata, dict)]
        metadata_job_types = sorted(
            {
                str(metadata.get("job_type"))
                for metadata in selected_metadata
                if metadata.get("job_type") is not None
            }
        )
        metadata_signals = {
            "selected_assets_with_runtime_version": sum(
                1 for metadata in selected_metadata if metadata.get("runtime_version") == runtime.runtime_version
            ),
            "selected_assets_with_job_id": sum(
                1 for metadata in selected_metadata if metadata.get("job_id") is not None
            ),
            "selected_assets_with_job_type": sum(
                1 for metadata in selected_metadata if metadata.get("job_type") is not None
            ),
            "selected_assets_with_external_task_id": sum(
                1 for metadata in selected_metadata if metadata.get("external_task_id") is not None
            ),
            "selected_assets_with_materialization_status": sum(
                1 for metadata in selected_metadata if metadata.get("materialization_status") is not None
            ),
            "selected_metadata_job_types": metadata_job_types,
        }
        association = {
            "association_method": "project_id + required_asset_types + asset_metadata.runtime_version",
            "runtime_version_filter_status": (
                "tentative_confirmed_by_data" if selected else "tentative_unconfirmed_no_matches"
            ),
            "association_strength": "tentative_metadata_backed",
            "selected_runtime_version": runtime.runtime_version,
            "candidate_asset_count": len(candidates),
            "selected_asset_count": len(selected),
            "selected_asset_ids": [str(asset.id) for asset in selected],
            "selected_asset_types": [asset.asset_type for asset in selected],
            "metadata_signal_counts": metadata_signals,
            "fallback_used": False,
        }
        return selected, association

    @staticmethod
    def _serialize_runtime(runtime: CompiledRuntime) -> dict[str, Any]:
        return {
            "runtime_id": str(runtime.id),
            "project_id": str(runtime.project_id),
            "runtime_version": runtime.runtime_version,
            "compile_status": runtime.compile_status,
            "runtime_payload": runtime.runtime_payload,
            "dispatch_status": runtime.dispatch_status,
            "dispatch_summary": runtime.dispatch_summary,
            "last_error_code": runtime.last_error_code,
            "last_error_message": runtime.last_error_message,
            "compile_started_at": runtime.compile_started_at.isoformat() if runtime.compile_started_at else None,
            "compile_finished_at": runtime.compile_finished_at.isoformat() if runtime.compile_finished_at else None,
            "created_at": runtime.created_at.isoformat() if runtime.created_at else None,
        }

    @staticmethod
    def _serialize_job(job: Job) -> dict[str, Any]:
        return {
            "job_id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "attempt_count": job.attempt_count,
            "max_attempts": job.max_attempts,
            "external_task_id": job.external_task_id,
            "error_code": job.error_code,
            "provider_name": job.provider_name,
            "payload": job.payload,
            "result_payload": job.result_payload,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }

    @staticmethod
    def _serialize_asset(asset: Asset) -> dict[str, Any]:
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


def build_markdown_summary(verdict: dict[str, Any]) -> str:
    jobs = verdict["evidence"].get("jobs", [])
    assets = verdict["evidence"].get("assets", [])
    objects = verdict["object_store"].get("objects", [])
    baseline_freeze = verdict.get("baseline_freeze", {})

    def render_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
        if not rows:
            return "(none)"
        header = "| " + " | ".join(columns) + " |"
        divider = "|" + "|".join(["---"] * len(columns)) + "|"
        body = [
            "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
            for row in rows
        ]
        return "\n".join([header, divider, *body])

    return textwrap.dedent(
        f"""
        # Baseline Gate Verdict

        ## Conclusion

        - verdict: `{verdict['verdict']}`
        - summary: {verdict['summary']}
        - executed_at: `{verdict['executed_at']}`
        - project_id: `{verdict['project_id']}`
        - runtime_id: `{verdict['runtime_id']}`
        - runtime_version: `{verdict['runtime_version']}`

        ## Layer Results

        - baseline_freeze: `{verdict['baseline_freeze']['status']}`
        - compile_dispatch: `{verdict['compile_dispatch']['status']}`
        - runtime_completion: `{verdict['runtime_completion']['status']}`
        - asset_materialization: `{verdict['asset_materialization']['status']}`
        - object_store: `{verdict['object_store']['status']}`

        ## Baseline Freeze

        - status: `{baseline_freeze.get('status')}`
        - checks:

        ```json
        {json.dumps(baseline_freeze.get('checks', {{}}), ensure_ascii=False, indent=2)}
        ```

        - settings_snapshot:

        ```json
        {json.dumps(verdict['evidence'].get('settings_snapshot', {{}}), ensure_ascii=False, indent=2)}
        ```

        - compose_snapshot:

        ```json
        {json.dumps(verdict['evidence'].get('compose_snapshot', {{}}), ensure_ascii=False, indent=2)}
        ```

        ## Jobs

        {render_table(jobs, ['job_id', 'job_type', 'status', 'external_task_id', 'error_code'])}

        ## Assets

        {render_table(assets, ['asset_id', 'asset_type', 'status', 'bucket_name', 'object_key', 'content_type'])}

        ## Object Store

        {render_table(objects, ['bucket_name', 'object_key', 'exists', 'size', 'content_type'])}

        ## Warnings

        ```json
        {json.dumps(verdict['warnings'], ensure_ascii=False, indent=2)}
        ```

        ## Drifts

        ```json
        {json.dumps(verdict['drifts'], ensure_ascii=False, indent=2)}
        ```

        ## Failures

        ```json
        {json.dumps(verdict['failures'], ensure_ascii=False, indent=2)}
        ```
        """
    ).strip() + "\n"


def resolve_output_path(candidate: Path | None, fallback_name: str) -> Path:
    if candidate is not None:
        return candidate
    return REPO_ROOT / fallback_name


def parse_args() -> GateContext:
    parser = argparse.ArgumentParser(description="Production baseline gate skeleton.")
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--compile-reason", default=DEFAULT_COMPILE_REASON)
    parser.add_argument("--mode", default=DEFAULT_MODE)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-interval-seconds", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args()
    return GateContext(
        repo_root=str(REPO_ROOT),
        project_id=args.project_id,
        compile_reason=args.compile_reason,
        mode=args.mode,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        output_json=args.output_json,
        output_md=args.output_md,
    )


def main() -> int:
    ctx = parse_args()
    gate = BaselineGate(ctx)
    verdict = gate.run()

    output_json = resolve_output_path(ctx.output_json, DEFAULT_JSON_NAME)
    output_md = resolve_output_path(ctx.output_md, DEFAULT_MD_NAME)
    output_json.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(build_markdown_summary(verdict), encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": verdict["verdict"],
                "runtime_id": verdict["runtime_id"],
                "runtime_version": verdict["runtime_version"],
                "output_json": str(output_json),
                "output_md": str(output_md),
            },
            ensure_ascii=False,
        )
    )
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
