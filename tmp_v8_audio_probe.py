from minio import Minio
from app.core.config import settings
client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=settings.minio_secure)
key = 'projects/656ac6b1-ecb8-4f45-9f45-556be5915168/runtime/v8/render_voice/5a07a1be-aec9-4ec1-8e3e-92e1a127481d.wav'
stat = client.stat_object(settings.minio_bucket_audio, key)
print(settings.minio_bucket_audio, key, stat.size, getattr(stat, 'content_type', None), sep='\t')
