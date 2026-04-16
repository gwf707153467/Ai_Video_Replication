import json
import urllib.request

url = 'http://127.0.0.1:8000/api/v1/compile'
payload = {
    'project_id': '656ac6b1-ecb8-4f45-9f45-556be5915168',
    'compile_reason': 'manual_runtime_validation',
    'compile_options': {'mode': 'manual_runtime_validation'},
    'auto_version': True,
    'dispatch_jobs': True,
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
print('BEGIN_COMPILE_DISPATCH', flush=True)
with urllib.request.urlopen(req, timeout=120) as resp:
    print('STATUS', resp.status, flush=True)
    print('BODY', resp.read().decode('utf-8'), flush=True)
print('END_COMPILE_DISPATCH', flush=True)
