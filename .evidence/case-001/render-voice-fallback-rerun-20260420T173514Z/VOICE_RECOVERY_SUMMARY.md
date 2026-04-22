# case-001 voice recovery summary

## What changed

`render_voice` was updated to tolerate `missing_vbus` at runtime by synthesizing a minimal fallback narration from the compiled sequence/SPU context when no VBU with `script_text` exists.

This aligns the executor with the current compile-validator behavior, where `missing_vbus` is only a warning and not a compile-stopping error.

## Live runtime outcome

Runtime:

- `runtime_version = v21`
- `runtime_id = 03bc44df-6771-4021-a1e6-b2834739ef05`

Final job states:

- `compile`: `succeeded`
- `render_image`: `succeeded`
- `render_video`: `succeeded`
- `render_voice`: `succeeded`
- `merge`: `failed`

## Materialized assets

Recovered assets in `v21`:

- generated image
  - bucket: `generated-images`
  - key: `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v21/render_image/bee21cd5-cbad-4a06-a54d-725a1ab482c4.png`

- generated video
  - bucket: `generated-videos`
  - key: `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v21/render_video/6aaa4884-b4f5-4916-8ad8-3080ca4fc115.mp4`

- generated audio
  - bucket: `audio-assets`
  - key: `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v21/render_voice/1a5acfd9-792a-4c1f-a2e2-0c5ac3b84796.wav`

Still failing:

- export / merge
  - bucket: `exports`
  - key: `projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v21/merge/v21-5ac2b1b1-c763-4ff5-8e83-dc88fa1e3e8f.mp4`
  - error code: `merge_execution_not_ready`

## Practical interpretation

This means the media-generation stack is now recovered for the current case:

- image generation: working
- video generation: working
- voice generation: working

The only remaining blocker for end-to-end completion is now:

- `merge.runtime`

## Next blocker

Current top blocker:

- `merge_execution_not_ready`

So the next highest-signal task is to implement or restore the real merge/export path.
