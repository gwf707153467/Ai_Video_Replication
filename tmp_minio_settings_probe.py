from app.core.config import settings
print('minio_endpoint\t' + settings.minio_endpoint)
print('reference\t' + settings.minio_bucket_reference)
print('generated_images\t' + settings.minio_bucket_generated_images)
print('generated_videos\t' + settings.minio_bucket_generated_videos)
print('audio\t' + settings.minio_bucket_audio)
print('exports\t' + settings.minio_bucket_exports)
print('runtime\t' + settings.minio_bucket_runtime)
