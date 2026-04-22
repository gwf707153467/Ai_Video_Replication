# case-001 / downstream-blocker-01 / render_video-gemini-compat archive (upstream-ready, minimal)

## 1. Executive summary

The highest-confidence conclusion for the historical Google video error
`400 INVALID_ARGUMENT: durationSeconds out of bound`
can now be narrowed to the following:

- The historical failure was **not** caused by the local stack sending the wrong `durationSeconds` value, rewriting it, or contaminating it before the final outbound request.
- Under a minimal direct-call matrix using the same account, same API surface, same model, same prompt, same `sampleCount=1`, and with `generateAudio` omitted, **only** `durationSeconds=5` fails, while `4/6/8` are accepted successfully.
- Therefore, the current blocker is much more consistent with a **Google service-side / interface-compatibility / account-capability-matrix anomaly** than with a local request-assembly bug.

One-line summary:
**Under the current `veo-3.1-generate-preview` + Generative Language `v1beta` path, `durationSeconds=5` shows a reproducible value-specific anomaly.**

---

## 2. Scope and fixed context

This archive is strictly limited to:

- case: `case-001`
- blocker: `downstream-blocker-01`
- scope: `render_video-gemini-compat`

Fixed business/runtime context:

- `project_id=656ac6b1-ecb8-4f45-9f45-556be5915168`
- `runtime_version=v17`
- `job_id=cd591b28-fd78-4723-95bf-33d1961bc543`
- `compiled_runtimes.runtime_payload.sequences[0].spus[0].duration_ms=5000`
- `primary_spu.duration_ms=5000`
- `provider_inputs=null`
- `provider_inputs.duration_seconds=None`
- one-shot read-only Python verification:
  - `provider_inputs.duration_seconds=None`
  - `primary_spu.duration_ms=5000`
  - `generation_options.duration_seconds=5`

---

## 3. Historical evidence already locked

Historical evidence directory:

- `.evidence/case-001/render-video-gemini-compat-request-capture-20260420T153612Z/`

Key files:

- `latest_predict_long_running.json`
- `raw_http_replay.json`
- `request_events.jsonl`
- `runtime_snapshot_final.json`
- `run_summary.json`
- `BLOCKER_SUMMARY.md`

### 3.1 The local stack was sending `durationSeconds=5`

The value `5` was fixed consistently across runtime inputs, executor resolution, provider client config, SDK materialization, and final request reconstruction:

- runtime/job/executor input chain showed `duration_seconds=5`
- provider client config showed `duration_seconds=5`
- last-hop SDK request dict showed `request_dict.parameters.durationSeconds=5`
- real outbound HTTP body contained `parameters.durationSeconds=5`
- `generateAudio` was not sent

This means the historical failure happened while the actual outbound request body already contained `durationSeconds=5`.

### 3.2 The historical failure contradicts the accepted range stated by the error itself

Even with the real outbound body explicitly containing:

- `parameters.sampleCount = 1`
- `parameters.durationSeconds = 5`
- `parameters.negativePrompt = ...`
- `generateAudio` absent

Google still returned:

- `400 INVALID_ARGUMENT`
- `The number value for durationSeconds is out of bound. Please provide a value between 4 and 8, inclusive.`

### 3.3 Raw HTTP replay reproduced the same failure

The same request body was replayed directly to:

- `https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning`

The replay still returned the same `400 INVALID_ARGUMENT` with the same `durationSeconds out of bound` message.

This materially lowers the probability that the problem is caused by:

- local app request assembly
- local executor normalization
- SDK-side serialization corruption

---

## 4. New minimal direct-call matrix

Additional script:

- `scripts/case_001_gemini_duration_matrix.py`

Real execution conditions:

- executed inside `avr_app` container
- SDK: `google-genai==1.73.1`
- API key: `GOOGLE_API_KEY` from `.env`
- API surface: Generative Language `v1beta`
- endpoint: `https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning`
- model: `veo-3.1-generate-preview`
- same historical prompt
- same historical negative prompt
- fixed `sampleCount=1`
- `generateAudio` omitted
- only variable changed: `durationSeconds ∈ {4,5,6,8}`
- `--skip-poll` was used, so this test only measures request-acceptance behavior

Evidence directory:

- `.evidence/case-001/render-video-gemini-duration-matrix-20260421T121943Z`

Key outputs:

- `experiment_plan.json`
- `run_log.txt`
- `sdk_duration_4.json`
- `sdk_duration_5.json`
- `sdk_duration_6.json`
- `sdk_duration_8.json`
- `duration_matrix_summary.json`
- `FINAL_ASSESSMENT.md`
- `container_google_genai_version.txt`
- `container_stdout.json`

---

## 5. Matrix result

Matrix summary:

- `model=veo-3.1-generate-preview`
- `api_surface=generative-language-v1beta-via-google-genai`
- `sdk_version=1.73.1`
- `durations_tested=[4,5,6,8]`
- `pattern=only_5_failed`

Per-value result:

- `duration=4`: accepted successfully
  - operation: `models/veo-3.1-generate-preview/operations/0o9t01gurlcn`
- `duration=5`: failed
  - error_type: `ClientError`
  - error_message: `400 INVALID_ARGUMENT. {'error': {'code': 400, 'message': 'The number value for \`durationSeconds\` is out of bound. Please provide a value between 4 and 8, inclusive.', 'status': 'INVALID_ARGUMENT'}}`
- `duration=6`: accepted successfully
  - operation: `models/veo-3.1-generate-preview/operations/98ch47v9ayib`
- `duration=8`: accepted successfully
  - operation: `models/veo-3.1-generate-preview/operations/8spsno6hbwtg`

In particular, `sdk_duration_5.json` also fixes the following facts:

- `config_dump.duration_seconds = 5`
- `request_body_expected.parameters.durationSeconds = 5`
- the response still returns the same `out of bound` error

This answers a critical question:

**The failure is not affecting all values inside the nominally accepted range. It is specific to `5`.**

---

## 6. Best-supported conclusion

Based on three evidence layers —
(1) historical real outbound request capture,
(2) raw HTTP replay, and
(3) the current minimal direct-call duration matrix —
the most defensible conclusion is:

### 6.1 Directions that should now be ruled out or heavily downgraded

The following should no longer be treated as the main root-cause hypothesis:

- the local stack sent the wrong `durationSeconds`
- the local stack rewrote `5` into some other value
- `generateAudio` contaminated the video request
- the SDK locally serialized `durationSeconds=5` into an invalid value

### 6.2 Highest-confidence root-cause direction at the current boundary

More credible explanations are now:

- Google service-side validation defect
- compatibility anomaly in the preview model under the current Generative Language `v1beta` integration
- undocumented account/region/model capability-matrix behavior specific to `durationSeconds=5`
- mismatch between documented/returned range semantics and actual backend behavior

### 6.3 Upstream-ready wording

Recommended blocker wording:

> The historical Google `durationSeconds out of bound` failure was not caused by incorrect local duration propagation. Historical evidence already confirmed that the real outbound request body contained `parameters.durationSeconds=5` and did not include `generateAudio`; replaying the same body via raw HTTP returned the same 400 response. In addition, under a minimal direct-call matrix using the same account, same model, same Generative Language `v1beta` path, same prompt/negative prompt, and only varying `durationSeconds=4/5/6/8`, values `4/6/8` were accepted successfully while only `5` failed. This strongly suggests that the blocker is a Google service-side / interface-compatibility / capability-matrix anomaly rather than a local pipeline error.

---

## 7. Boundary of this conclusion

The following boundary must remain explicit:

- This conclusion is limited to request-acceptance behavior under the **current account + current model `veo-3.1-generate-preview` + current API surface `Generative Language v1beta` + current prompt conditions**.
- This conclusion does **not** prove that Vertex AI would show the same behavior.
- This conclusion does **not** prove that the preview model is globally unusable; it only shows a reproducible anomaly for `durationSeconds=5` under the current combination.
- This conclusion is strong enough to reject the old "local duration propagation was wrong" hypothesis, but it does not by itself reveal Google's internal backend cause.

---

## 8. Suggested blocker status update

Suggested status language:

- the blocker still exists, but its diagnosis should move from "local request assembly issue" to "Google upstream behavior / compatibility issue"
- there is no new local evidence justifying more work on duration assembly, executor normalization, or SDK payload reconstruction
- if further work is required, the highest-value next directions are:
  - upstream/platform compatibility verification (Generative Language vs Vertex AI)
  - or an explicitly acknowledged product-side workaround (for example, avoiding `durationSeconds=5`) if a workaround is acceptable as a temporary mitigation rather than a root-cause fix
