import json, time, urllib.request

scheme = 'http'
host = '127.0.0.1:8000'
api_prefix = '/api/v1'
base = f"{scheme}://{host}{api_prefix}"
headers = {'Content-Type': 'application/json'}


def req(method, path, payload=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
    r = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=120) as resp:
        body = resp.read().decode('utf-8')
        return resp.status, json.loads(body)


project_payload = {
    'name': 'eighth-batch-render-image-smoke',
    'status': 'draft',
    'source_market': 'US',
    'source_language': 'en-US',
    'notes': 'Minimal real smoke for render_image chain',
}
status, project = req('POST', '/projects', project_payload)
print('PROJECT_STATUS', status)
print('PROJECT', json.dumps(project, ensure_ascii=False))
project_id = project['id']

sequence_payload = {
    'project_id': project_id,
    'sequence_index': 1,
    'sequence_type': 'hook',
    'persuasive_goal': 'Introduce the beauty product with a clean premium visual',
    'status': 'draft',
}
status, sequence = req('POST', '/sequences', sequence_payload)
print('SEQUENCE_STATUS', status)
print('SEQUENCE', json.dumps(sequence, ensure_ascii=False))
sequence_id = sequence['id']

spu_payload = {
    'project_id': project_id,
    'sequence_id': sequence_id,
    'spu_code': 'SPU-001',
    'display_name': 'Beauty serum hero shot',
    'asset_role': 'primary_visual',
    'duration_ms': 5000,
    'generation_mode': 'veo_segment',
    'prompt_text': 'Create a premium TikTok beauty product hero image on pure white background, serum bottle centered vertically, clean studio lighting, realistic packaging detail, high-end cosmetic advertising look, 9:16 composition.',
    'negative_prompt_text': 'blurry, deformed packaging, extra objects, cropped product, watermark, text overlay',
    'visual_constraints': {'background': '#FFFFFF', 'style': 'studio_clean', 'platform': 'tiktok_9_16'},
    'status': 'draft',
}
status, spu = req('POST', '/spus', spu_payload)
print('SPU_STATUS', status)
print('SPU', json.dumps(spu, ensure_ascii=False))

status, validation = req('GET', f'/compile/validate/{project_id}')
print('VALIDATE_STATUS', status)
print('VALIDATE', json.dumps(validation, ensure_ascii=False))

compile_only_payload = {
    'project_id': project_id,
    'compile_reason': 'smoke_compile_only',
    'compile_options': {'mode': 'smoke_compile_only'},
    'auto_version': True,
    'dispatch_jobs': False,
}
status, compile_only = req('POST', '/compile', compile_only_payload)
print('COMPILE_ONLY_STATUS', status)
print('COMPILE_ONLY', json.dumps(compile_only, ensure_ascii=False))

compile_dispatch_payload = {
    'project_id': project_id,
    'compile_reason': 'smoke_compile_dispatch',
    'compile_options': {'mode': 'smoke_compile_dispatch'},
    'auto_version': True,
    'dispatch_jobs': True,
}
status, compile_dispatch = req('POST', '/compile', compile_dispatch_payload)
print('COMPILE_DISPATCH_STATUS', status)
print('COMPILE_DISPATCH', json.dumps(compile_dispatch, ensure_ascii=False))

runtime_version = compile_dispatch['runtime_version']
print('PROJECT_ID', project_id)
print('SEQUENCE_ID', sequence_id)
print('SPU_ID', spu['id'])
print('RUNTIME_VERSION', runtime_version)

for i in range(6):
    time.sleep(5)
    status, assets = req('GET', f'/assets/project/{project_id}')
    print(f'ASSETS_POLL_{i+1}_STATUS', status)
    print(f'ASSETS_POLL_{i+1}', json.dumps(assets, ensure_ascii=False))
