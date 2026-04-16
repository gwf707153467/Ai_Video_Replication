# runtime_terminal_sdk

> A minimal SDK for runtime terminal v1 terminal writes and snapshot reads.

> Repository note: in the current repository, the root project metadata still belongs to `ai-videos-replication` and `[project].readme` still points to the root `README.md`. This file is therefore a formal README candidate for the minimal `runtime_terminal_sdk` package boundary and does **not** replace the repository root README.

## Package summary

`runtime_terminal_sdk` is a minimal caller-side SDK for runtime terminal v1.
It is intentionally small and stable, and it only covers terminal writes and job snapshot reads.

This package exists to make the following integration path predictable and reusable:

```text
build context -> write terminal -> handle explicit errors -> verify by snapshot
```

The v1 boundary is intentionally frozen:
- terminal = terminal write + snapshot read
- public methods stay centered on `complete_job(...)`, `fail_job(...)`, and `get_job_snapshot(...)`
- the SDK does not redefine API contract or reopen complete / fail / snapshot semantics
- the SDK does not expand into claim, heartbeat, retry orchestration, or business arbitration

## What this package is

`runtime_terminal_sdk` is a minimal client package for runtime terminal v1.

Its public surface is intentionally centered on three actions only:

- `complete_job(...)`
- `fail_job(...)`
- `get_job_snapshot(...)`

This package is suitable for:
- worker reporters
- lightweight adapters
- caller-side runtime terminal integrations
- small internal SDK handoff scenarios

The package aims to be:
- minimal
- stable
- reusable
- handoff-friendly

## What this package is not

This package is **not**:

- a unified runtime platform SDK
- a claim client
- a heartbeat manager
- a retry orchestration framework
- a business-state arbiter
- a scheduler entrypoint

If your integration needs claim, heartbeat, retry scheduling, or business-state arbitration, those responsibilities should remain outside this package.

## Public surface

The minimal public surface stays centered on:

- `RuntimeTerminalClient`
- `RuntimeAttemptContext`
- minimal exception tree

Typical package layout:

```text
runtime_terminal_sdk/
├── client.py
├── models.py
├── errors.py
└── __init__.py
```

Recommended imports:

```python
from runtime_terminal_sdk import (
    RuntimeAttemptContext,
    RuntimeTerminalClient,
    RuntimeTerminalConflictError,
    RuntimeTerminalNotFoundError,
    RuntimeTerminalServerError,
    RuntimeTerminalTransportError,
    RuntimeTerminalValidationError,
)
```

`RuntimeAttemptContext` is used to keep the four identity fields from the same real attempt together:

- `job_id`
- `attempt_id`
- `worker_id`
- `claim_token`

Important reminder:

> `job_id / attempt_id / worker_id / claim_token` must come from the same real attempt. Do not reconstruct the four identity fields from multiple sources.

## Repository / packaging note

This README candidate is aligned to a minimal repo-local or internal package shape first.

Current repository facts:
- repository root project name is `ai-videos-replication`
- root project version is `0.1.0`
- root project `readme` still points to `README.md`
- current package include in `pyproject.toml` is `app*`

So, at the time of writing, this README should be treated as the formal candidate for a minimal `runtime_terminal_sdk` package boundary, not as proof that a separately published package already exists.

Recommended v1 packaging stance:
- small internal package or repo-local package first
- explicit exports only
- no sync / async dual-stack in v1
- no plugin or middleware framework
- no widened surface beyond terminal write + snapshot read

## Quick start

Recommended default flow:

```text
build context -> write terminal -> handle explicit errors -> verify by snapshot
```

Before any terminal write, remember:
- `completion_status` is not the same as `job_status`
- the SDK does not auto-repair payloads
- the SDK does not auto-replace `claim_token`
- the SDK does not auto-retry `409`

Example:

```python
from runtime_terminal_sdk import (
    RuntimeAttemptContext,
    RuntimeTerminalClient,
    RuntimeTerminalConflictError,
    RuntimeTerminalNotFoundError,
    RuntimeTerminalServerError,
    RuntimeTerminalTransportError,
    RuntimeTerminalValidationError,
)

client = RuntimeTerminalClient(
    base_url="https://runtime.example.internal",
    api_key="your-api-key",
)

ctx = RuntimeAttemptContext(
    job_id="job-123",
    attempt_id="attempt-7",
    worker_id="worker-video-a",
    claim_token="claim-9f3d",
)

try:
    result = client.complete_job(
        context=ctx,
        completion_status="SUCCEEDED",
        result_ref="minio://video-results/job-123/final.mp4",
        manifest_artifact_id=None,
        runtime_ms=31000,
        provider_runtime_ms=27000,
        upload_ms=1800,
        metadata_json={
            "provider": "veo",
            "pipeline": "beauty_replication_v1",
        },
    )

    snapshot = client.get_job_snapshot(job_id=ctx.job_id)

    print(result)
    print(snapshot)

except RuntimeTerminalConflictError:
    # Usually a state / lease / attempt-context conflict.
    # Do not auto-retry by default.
    raise
except RuntimeTerminalValidationError:
    # Usually a caller or payload construction issue.
    raise
except RuntimeTerminalNotFoundError:
    # Usually a wrong identifier or missing resource.
    raise
except RuntimeTerminalServerError:
    # Server-side or infrastructure-side failure.
    # Limited retry may be considered by the caller.
    raise
except RuntimeTerminalTransportError:
    # Transport failure should be handled separately from HTTP semantic errors.
    raise
```

If your flow ends in failure instead of success, call `fail_job(...)` with the same `RuntimeAttemptContext` rather than rebuilding identity from mixed sources.

Minimal failure-side example:

```python
client.fail_job(
    context=ctx,
    failure_reason="provider timeout",
    next_job_status="WAITING_RETRY",
    attempt_terminal_status="TIMED_OUT",
    metadata_json={"provider": "veo"},
)

snapshot = client.get_job_snapshot(job_id=ctx.job_id)
print(snapshot)
```

## Error handling

Use the following mental model:

| Status / category | Preferred interpretation | Default suggestion |
|---|---|---|
| 409 | state / lease / attempt-context conflict | do not auto-retry by default |
| 422 | caller or payload construction issue | fix request construction first |
| 404 | object missing or wrong identifier | verify identifiers and resource existence |
| 5xx | server or infrastructure issue | limited retry may be acceptable |
| transport error | network / transport failure | handle separately from HTTP semantic conflicts |

Additional reminders:
- `422` keeps FastAPI / Pydantic default validation behavior
- `409` is closer to a state or context conflict than a transient network retry signal
- a successful terminal write does not automatically mean the business side has consumed the expected state
- snapshot verification is recommended after `complete` / `fail`, especially on critical paths
- keep HTTP semantic errors and transport failures as separate branches in caller logic

## Boundary / non-goals

Keep the following boundary fixed:

- terminal = terminal write + snapshot read
- the SDK does not make business decisions for the caller
- the SDK does not auto-retry `409` conflicts
- the SDK does not auto-repair payloads
- the SDK does not auto-replace `claim_token`
- the SDK does not infer or synthesize attempt identity fields
- the SDK does not wrap FastAPI / Pydantic `422` into a new business-specific schema
- the facade write side must not bypass service and write repository state directly

Non-goals in v1:
- claim support
- heartbeat support
- retry orchestration
- scheduler entrypoints
- business arbitration
- large DTO frameworks
- plugin or middleware systems
- dual sync / async client stacks

## Related docs

For deeper details, read the following documents together with this README:

- `runtime_terminal_sdk_docs_index_v1.md`
- `runtime_terminal_sdk_exception_contract_note_v1.md`
- `runtime_terminal_sdk_packaging_note_v1.md`
- `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
- `runtime_terminal_sdk_usage_snippet_pack_v1.md`
- `runtime_terminal_sdk_scaffold_checklist_v1.md`
- `runtime_terminal_sdk_readme_handoff_note_v1.md`
- `runtime_terminal_caller_faq_v1.md`
- `runtime_terminal_language_specific_error_mapping_appendix_v1.md`

Recommended reading order for a new maintainer:
1. `runtime_terminal_sdk_docs_index_v1.md`
2. `runtime_terminal_sdk_exception_contract_note_v1.md`
3. `runtime_terminal_sdk_packaging_note_v1.md`
4. `runtime_terminal_minimal_sdk_scaffold_note_v1.md`
5. `runtime_terminal_sdk_usage_snippet_pack_v1.md`

## Handoff note

This README assumes the runtime terminal v1 boundary is frozen.

Do not reopen the following questions in this package README:
- whether terminal should become a scheduler entrypoint
- whether claim / heartbeat should be included
- whether `409` should be auto-retried by default
- whether caller payload issues should be silently repaired by the SDK
- whether the SDK should arbitrate business state transitions
- whether attempt identity fields can be reconstructed from mixed sources

If future work is needed, prefer additive documentation or a separate design track rather than silently expanding this README beyond the v1 boundary.
