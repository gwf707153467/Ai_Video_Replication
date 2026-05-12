import os

from app.core.config import settings


def resolve_test_database_url() -> str:
    explicit_url = os.getenv("RUNTIME_TERMINAL_TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    host_docker_internal_url = settings.database_url.replace("@postgres:", "@host.docker.internal:")
    if host_docker_internal_url != settings.database_url:
        return host_docker_internal_url

    return settings.database_url.replace("@postgres:", "@127.0.0.1:")
