from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://rag:rag@postgres:5432/rag"
    redis_url: str = "redis://redis:6379/0"

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "rag_chunks"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket: str = "rag-documents"
    minio_secure: bool = False

    embedding_provider: str = "voyage"
    embedding_model: str = "voyage-3"
    embedding_dim: int = 1024
    voyage_api_key: str = ""

    chunk_child_tokens: int = 220
    chunk_child_overlap: int = 40
    chunk_parent_tokens: int = 1000

    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    celery_concurrency: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
