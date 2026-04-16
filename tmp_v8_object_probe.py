from minio import Minio
from app.core.config import settings

client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

checks = [
    ('exports', 'projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/merge/v8-1c0e0b7b-a93c-4ac2-bb4f-21d860141d0e.mp4'),
    ('generated-videos', 'projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_video/5eb9398c-47f1-4107-bb3d-e3e15137ad91.mp4'),
    ('audio', 'projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_voice/5a07a1be-aec9-4ec1-8e3e-92e1a127481d.wav'),
    ('generated-images', 'projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_image/3607c6c1-ff4b-428b-b9a1-ebaf6ef22e36.png'),
]
print('endpoint\t' + settings.minio_endpoint, flush=True)
for bucket, key in checks:
    try:
        stat = client.stat_object(bucket, key)
        print('\t'.join([
            bucket,
            key,
            str(stat.size),
            str(getattr(stat, 'content_type', None)),
            'exists',
        ]), flush=True)
    except Exception as exc:
        print('\t'.join([bucket, key, 'ERR', type(exc).__name__, str(exc)]), flush=True)
