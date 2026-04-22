# Multi-case regression progress

## Current scope

The regression set has been expanded from one case to three frozen cases:

- `case-001`: original beauty/serum proof case
- `case-002`: handbag reference video replication case
- `case-003`: handbag commuter-market copy variant

The user-provided reference video was frozen at:

- `.evidence/case-002-reference-bag-video.mp4`

Reference SHA256:

- `5adb41e9067a93487f74a7b486c48746a7a383a3e2df3b5055cd51bcbaaeb52e`

## Added case artifacts

New payloads:

- `.evidence/case-002/compile_request_payload.json`
- `.evidence/case-003/compile_request_payload.json`

New manifests:

- `.evidence/case-002/input_manifest.json`
- `.evidence/case-003/input_manifest.json`

Registry:

- `.evidence/regression_cases_index.json`

## Regression suite changes

The regression suite now supports:

- multiple case payloads
- repeat count
- case-level delay via `--case-delay-seconds`
- unique evidence directory naming by case folder
- quota-aware classification

Quota-aware statuses:

- `PASS`: case completed and `final_output.mp4` exists
- `QUOTA_BLOCKED`: provider returned quota/rate-limit errors such as `429 RESOURCE_EXHAUSTED`
- `FAIL`: local/runtime failure not attributable to quota

## Latest evidence

### First multi-case attempt

Directory:

- `.evidence/regression/20260421T040200Z`

Result:

- suite: `PASS`
- caveat: evidence directory naming collision existed in the first implementation, so case directories were not independently preserved

### Corrected multi-case attempt

Directory:

- `.evidence/regression/20260421T040509Z`

Result:

- `case-002`: `PASS`
- `case-003`: failed due to `429 RESOURCE_EXHAUSTED`

`case-002` output:

- `.evidence/regression/20260421T040509Z/case-002-run-1/final_output.mp4`

`case-003` blocker:

- Google video generation returned `429 RESOURCE_EXHAUSTED`
- this is provider quota/rate-limit pressure, not a local pipeline failure

## Practical conclusion

The system has now moved beyond single-case validation:

- `case-001` full chain previously passed at runtime `v27`
- `case-002` full chain passed as an independent handbag regression case
- `case-003` is structurally valid but currently blocked by provider video quota

The next useful action is not more immediate reruns. It is to run the quota-aware suite after the Google video quota window resets.

Recommended command:

```powershell
python scripts\regression_suite.py --skip-baseline-gate --skip-unit-tests --case-delay-seconds 180 --case-payload .evidence\case-002\compile_request_payload.json --case-payload .evidence\case-003\compile_request_payload.json
```

For stronger stability sampling after quota reset:

```powershell
python scripts\regression_suite.py --skip-baseline-gate --skip-unit-tests --case-delay-seconds 180 --repeat 2 --case-payload .evidence\case-002\compile_request_payload.json --case-payload .evidence\case-003\compile_request_payload.json
```
