from collections import Counter

from app.db.models import CompiledRuntime, Job


class RuntimeStateService:
    TERMINAL_SUCCESS_STATUSES = {"succeeded"}
    TERMINAL_FAILURE_STATUSES = {"failed"}
    ACTIVE_STATUSES = {"queued", "dispatched", "running"}

    @classmethod
    def build_summary(cls, db, runtime: CompiledRuntime) -> dict:
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
        job_entries = [
            {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "attempt_count": job.attempt_count,
                "max_attempts": job.max_attempts,
                "external_task_id": job.external_task_id,
                "error_code": job.error_code,
            }
            for job in jobs
        ]

        return {
            "runtime_version": runtime.runtime_version,
            "job_count": len(jobs),
            "queued_job_count": counts.get("queued", 0),
            "dispatched_job_count": counts.get("dispatched", 0),
            "running_job_count": counts.get("running", 0),
            "succeeded_job_count": counts.get("succeeded", 0),
            "failed_job_count": counts.get("failed", 0),
            "jobs": job_entries,
        }

    @classmethod
    def derive_compile_status(cls, summary: dict, current_status: str) -> str:
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

    @classmethod
    def derive_dispatch_status(cls, summary: dict, current_status: str) -> str:
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

    @classmethod
    def refresh_runtime_status(cls, db, runtime: CompiledRuntime) -> CompiledRuntime:
        summary = cls.build_summary(db, runtime)
        runtime.dispatch_summary = summary
        runtime.dispatch_status = cls.derive_dispatch_status(summary, runtime.dispatch_status)
        runtime.compile_status = cls.derive_compile_status(summary, runtime.compile_status)

        failed_jobs = [job for job in summary.get("jobs", []) if job.get("status") == "failed"]
        if failed_jobs:
            latest_failed = failed_jobs[-1]
            runtime.last_error_code = latest_failed.get("error_code") or runtime.last_error_code
        elif runtime.compile_status != "failed":
            runtime.last_error_code = None
            runtime.last_error_message = None

        return runtime
