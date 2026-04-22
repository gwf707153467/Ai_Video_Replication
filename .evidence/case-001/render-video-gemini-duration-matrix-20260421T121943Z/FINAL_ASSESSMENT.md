# FINAL ASSESSMENT

- model: `veo-3.1-generate-preview`
- api_surface: `generative-language-v1beta-via-google-genai`
- durations_tested: `[4, 5, 6, 8]`
- pattern: `only_5_failed`

## Matrix

- duration=4: ok=True, error_type=None, error_message=None
- duration=5: ok=False, error_type=ClientError, error_message=400 INVALID_ARGUMENT. {'error': {'code': 400, 'message': 'The number value for `durationSeconds` is out of bound. Please provide a value between 4 and 8, inclusive.', 'status': 'INVALID_ARGUMENT'}}
- duration=6: ok=True, error_type=None, error_message=None
- duration=8: ok=True, error_type=None, error_message=None

## Boundary

This assessment is limited to request-acceptance behavior under the current account/model/API surface. It does not infer that local duration propagation was wrong, because historical evidence already fixed the outbound request body at durationSeconds=5.
