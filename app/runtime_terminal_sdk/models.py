from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeAttemptContext:
    job_id: str
    attempt_id: str
    worker_id: str
    claim_token: str
