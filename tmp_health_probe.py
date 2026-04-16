import json
import sys
import urllib.request

url = 'http://127.0.0.1:8000/health'
print('BEGIN_HEALTH_PROBE', flush=True)
with urllib.request.urlopen(url, timeout=15) as resp:
    body = resp.read().decode('utf-8')
    print('STATUS', resp.status, flush=True)
    print('BODY', body, flush=True)
print('END_HEALTH_PROBE', flush=True)
