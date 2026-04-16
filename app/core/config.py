from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai_videos_replication"
    app_env: str = "development"
    log_level: str = "INFO"

    postgres_db: str = "ai_videos_replication"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/ai_videos_replication"

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_reference: str = "reference"
    minio_bucket_generated_images: str = "generated-images"
    minio_bucket_generated_videos: str = "generated-videos"
    minio_bucket_audio: str = "audio"
    minio_bucket_exports: str = "exports"
    minio_bucket_runtime: str = "runtime"

    google_api_key: str = ""
    google_video_model: str = ""
    google_image_model: str = ""
    google_tts_model: str = ""

    default_target_market: str = "US"
    default_target_language: str = "en-US"


settings = Settings()
