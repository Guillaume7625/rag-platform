from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_port: int = 8000
    log_level: str = "INFO"
    root_path: str = ""

    # Explicit allowlist of browser origins allowed to call the API. Parsed
    # from env as a JSON array, e.g. CORS_ORIGINS=["http://localhost:3000"].
    # Default matches the dev web container; production must override.
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+psycopg://rag:rag@postgres:5432/rag"
    redis_url: str = "redis://redis:6379/0"

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "rag_chunks"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket: str = "rag-documents"
    minio_secure: bool = False

    jwt_secret: str = "change_me_in_prod"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 1440

    # --- Embeddings ---
    embedding_provider: str = "voyage"  # voyage | bge | fallback
    embedding_model: str = "voyage-3"
    embedding_dim: int = 1024
    voyage_api_key: str = ""

    # --- Reranker ---
    reranker_provider: str = "cohere"  # cohere | voyage | lexical
    reranker_model: str = "rerank-v3.5"
    cohere_api_key: str = ""

    # --- LLM ---
    llm_provider: str = "anthropic"  # anthropic | openai
    llm_small_model: str = "claude-haiku-4-5-20251001"
    llm_large_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # --- IDF ---
    idf_enabled: bool = True

    # --- Embedding cache ---
    embedding_cache_enabled: bool = True
    embedding_cache_ttl: int = 3600

    # --- Query expansion ---
    query_expansion_enabled: bool = True
    query_expansion_count: int = 2

    # --- Reranker cache ---
    rerank_cache_enabled: bool = True
    rerank_cache_ttl: int = 1800
    rerank_early_stop_threshold: float = 0.85
    rerank_first_pass_size: int = 10

    # --- Retrieval ---
    retrieval_top_k: int = 50
    rerank_top_k: int = 20
    context_top_k: int = 6
    context_token_budget: int = 4000
    context_score_threshold: float = 0.15
    context_max_parents: int = 10

    # --- Celery ---
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
