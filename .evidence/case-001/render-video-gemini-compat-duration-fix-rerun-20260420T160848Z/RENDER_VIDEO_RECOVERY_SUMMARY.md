# case-001 render_video recovery summary

## What changed

The local duration normalization logic in [executors.py](D:/Documents/Codex/deerflow2.0/backend/.deer-flow/threads/4cac9b0a-8397-4256-bcd3-46a38345d163/user-data/workspace/Ai_Videos_Replication/app/workers/executors.py) was updated from a continuous clamp (`4..8`) to discrete Veo-compatible normalization (`4`, `6`, `8`).

Live worker verification after syncing the fix:

- `2 -> 4`
- `5 -> 6`
- `7 -> 8`
- `12 -> 8`
- `1500ms -> 4`
- `5000ms -> 6`
- `7000ms -> 8`
- `12000ms -> 8`

## Real rerun result

Rerun evidence directory:

- `render-video-gemini-compat-duration-fix-rerun-20260420T160848Z`

Key result:

- runtime: `v19`
- render_video job id: `cbe984b0-f53f-4416-8c95-7c4ccffd2a19`
- render_video status: `succeeded`
- generated video asset status: `materialized`
- generated video object:
  - bucket: `generated-videos`
  - key: `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v19/render_video/cbe984b0-f53f-4416-8c95-7c4ccffd2a19.mp4`

This means the original `durationSeconds out of bound` blocker for `render_video` is cleared in the live path.

## What is still failing

The overall runtime is still not end-to-end healthy because other jobs are failing:

- `render_image`
  - error: `google_image_generation_failed`
  - detail: `models/gemini-3.1-flash-image-preview is not found for API version v1beta`
- `render_voice`
  - error: `runtime_vbu_missing`
- `merge`
  - error: `merge_execution_not_ready`

So the current state is:

- `render_video`: recovered
- full runtime / final merged output: still blocked by non-video jobs

## Practical interpretation

Within the requested scope, this is a successful recovery:

- the duration normalization bug was real
- it was fixed locally
- the fix was verified in the live worker
- the real `render_video` chain now runs through and materializes a generated video object

Outside that scope, the project is still not yet fully production-ready because image, voice, and merge remain unresolved.
