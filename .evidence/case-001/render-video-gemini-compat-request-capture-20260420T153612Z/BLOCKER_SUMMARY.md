# case-001 render_video Gemini/Veo blocker summary

## Scope

This record is limited to:

- `case-001`
- `downstream-blocker-01`
- `render_video-gemini-compat`

Out of scope:

- `render_voice`
- `merge`
- `final_output.mp4`
- `.env drift`
- broader refactors

## What was executed

One controlled diagnostic rerun was executed against the real app/worker path with a minimal temporary observation patch around the final Google video request call. The patch was removed immediately after evidence capture.

Key evidence files in this directory:

- `latest_predict_long_running.json`
- `request_events.jsonl`
- `raw_http_replay.json`
- `runtime_snapshot_final.json`
- `run_summary.json`

## Hard findings

### 1. Real outbound request from the worker was captured

From `request_events.jsonl` and `latest_predict_long_running.json`:

- request path: `models/veo-3.1-generate-preview:predictLongRunning`
- request body included:
  - `parameters.sampleCount = 1`
  - `parameters.durationSeconds = 5`
  - `parameters.negativePrompt = "..."`
- `generateAudio` was **not** present

This is not a theoretical reconstruction. It is the real request captured at the last hop before the Google client raised the error.

### 2. The real rerun still failed with the same Google error

From `latest_predict_long_running.json` and `runtime_snapshot_final.json`:

- Google returned:
  - `400 INVALID_ARGUMENT`
  - `The number value for durationSeconds is out of bound. Please provide a value between 4 and 8, inclusive.`

This happened even though the captured outbound request explicitly contained `durationSeconds = 5`.

### 3. Raw HTTP replay reproduced the same failure without the SDK wrapper

From `raw_http_replay.json`:

- the same request body was replayed directly to:
  - `https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning`
- request body still contained:
  - `parameters.durationSeconds = 5`
- the direct HTTP call still returned:
  - `400 INVALID_ARGUMENT`
  - same `durationSeconds out of bound` message

This meaningfully reduces the likelihood that the bug is caused by local app request assembly or by SDK-side serialization corruption.

## Acceptance status

### Acceptance #1

`render_video` no longer reproduces `generate_audio parameter is not supported in Gemini API`.

Status: `passed`

### Acceptance #2

`generated-videos/...mp4` object actually appears.

Status: `failed`

Direct blocker:

- Google rejects the request with `durationSeconds out of bound`
- therefore no successful generated video object is materialized

## Conclusion inside current task boundary

Within the current boundary, the strongest supported conclusion is:

1. The local app is sending `durationSeconds = 5`.
2. `generateAudio` is not being sent.
3. A direct raw HTTP replay of the same body also fails with the same Google error.

So this blocker now looks **much more like downstream/API-side behavior** than:

- local app input resolution
- local executor normalization
- SDK local request serialization

## Important compatibility note

On `2026-04-20`, the current runtime is still configured to use:

- `veo-3.1-generate-preview`

Additional model visibility probe from the live app environment showed:

- `veo-3.1-generate-preview`: available on the current `v1beta` path
- `veo-3.1-fast-generate-preview`: available on the current `v1beta` path
- `veo-3.1-generate-001`: not found on the current `v1beta` path
- `veo-3.1-fast-generate-001`: not found on the current `v1beta` path

This suggests that any migration from preview to `-001` is **not** a simple model-name swap in the current Generative Language `v1beta` integration. It likely requires a different platform path or integration mode.

Related official documentation checked on `2026-04-20`:

- [Veo 3.1 generate preview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate-preview)

## Recommended next actions

### Highest-signal next step

Open an upstream compatibility investigation with the captured evidence package from this directory, centered on:

- real outbound request path
- real outbound request body
- direct raw HTTP replay result
- repeated `durationSeconds out of bound` despite `durationSeconds = 5`

### Practical local follow-up

If local work must continue before upstream clarification:

1. verify whether this workflow should use Vertex AI instead of the current Generative Language `v1beta` path for Veo 3.1 production models
2. verify whether `veo-3.1-generate-preview` is exhibiting degraded or inconsistent behavior in the current integration despite still being discoverable
3. avoid spending more time on executor normalization or SDK payload reconstruction unless new contradictory evidence appears

## Temporary patch status

The diagnostic observation patch used for this run has already been reverted after evidence capture.
