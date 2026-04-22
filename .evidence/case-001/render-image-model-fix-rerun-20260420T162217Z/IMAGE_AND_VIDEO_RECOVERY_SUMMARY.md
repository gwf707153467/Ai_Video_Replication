# case-001 image and video recovery summary

## What changed

Two live-path issues were addressed:

1. `render_video`
   - duration normalization was changed to discrete Veo-compatible values: `4`, `6`, `8`
2. `render_image`
   - live `GOOGLE_IMAGE_MODEL` was changed from `gemini-3.1-flash-image-preview`
   - to `imagen-4.0-fast-generate-001`
   - app and worker were rebuilt and recreated from the current workspace

## Live runtime outcome

Runtime:

- `runtime_version = v20`
- `runtime_id = d30d8bf8-0d75-4c2f-9f76-d66e1dc98fb8`

After the `v20` rerun completed:

- `compile`: `succeeded`
- `render_image`: `succeeded`
- `render_video`: `succeeded`
- `render_voice`: `failed`
- `merge`: `failed`

## Materialized assets

Recovered assets:

- generated image
  - bucket: `generated-images`
  - key: `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v20/render_image/6e07f063-45db-4685-8663-305c91debaab.png`
  - status: `materialized`

- generated video
  - bucket: `generated-videos`
  - key: `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v20/render_video/37402605-776e-4b5f-b399-0abe4b2d5d25.mp4`
  - status: `materialized`

Still failing:

- voice asset
  - error code: `runtime_vbu_missing`
- export asset
  - error code: `merge_execution_not_ready`

## Interpretation

This means the two previously hardest media-generation blockers are now cleared in the live path:

- `render_image` recovered
- `render_video` recovered

The system is still not fully end-to-end complete because:

- `render_voice` is failing due to missing runtime VBU/script text
- `merge` is failing because the real mux/export chain is still not implemented

## Practical status

Current state:

- image generation: working
- video generation: working
- voice generation: blocked
- final merged export: blocked

So the next highest-signal blockers are now:

1. `render_voice` (`runtime_vbu_missing`)
2. `merge` (`merge_execution_not_ready`)
