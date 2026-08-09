"""
Core application configuration.
Uses pydantic-settings for type-safe environment variable management.
"""

from functools import lru_cache
from typing import Literal
from app.core.logging import get_logger
from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = get_logger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = "AI ERP Assistant"
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------
    api_v1_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # -------------------------------------------------------------------------
    # OpenAI
    # -------------------------------------------------------------------------
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    # openai_model: str = "gpt-4o"
    # openai_embedding_model: str = "text-embedding-3-large"
    # openai_embedding_dimensions: int = 3072
    # openai_max_tokens: int = 4096
    # openai_temperature: float = 0.1
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")

    use_ollama: bool = Field(default=True, alias="USE_OLLAMA")

    ollama_base_url: str = Field(default="http://ollama:11434", alias="OLLAMA_BASE_URL")

    ollama_model: str = Field(default="qwen2.5:7b", alias="OLLAMA_MODEL")

    ollama_embedding_model: str = Field(
        default="nomic-embed-text", alias="OLLAMA_EMBEDDING_MODEL"
    )

    ollama_embedding_dimensions: int = 768

    ollama_temperature: float = 0.1

    ollama_max_tokens: int = 4096
    ollama_request_timeout: int = 120
    ollama_num_predict: int = 512
    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(..., alias="DATABASE_URL")
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_url: str = "redis://redis:6379/0"
    redis_session_ttl: int = 86400  # 24 hours
    redis_cache_ttl: int = 3600  # 1 hour

    # -------------------------------------------------------------------------
    # Qdrant
    # -------------------------------------------------------------------------
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "erp_documents"
    qdrant_vector_size: int = 768

    # -------------------------------------------------------------------------
    # RAG
    # -------------------------------------------------------------------------
    chunk_size: int = 400
    chunk_overlap: int = 100
    rag_top_k: int = 10
    rag_rerank_top_k: int = 10
    rag_score_threshold: float = 0.45
    query_rewrite_enabled: bool = True
    hybrid_search_enabled: bool = True
    hybrid_alpha: float = 0.7

    # -------------------------------------------------------------------------
    # Agents / LangGraph
    # -------------------------------------------------------------------------
    agent_max_retries: int = 3
    agent_retry_delay: float = 1.0
    agent_timeout: int = 60
    max_conversation_history: int = 20
    memory_summarization_threshold: int = 15

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    langfuse_enabled: bool = True
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # -------------------------------------------------------------------------
    # Celery
    # -------------------------------------------------------------------------
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    celery_concurrency: int = 1

    # -------------------------------------------------------------------------
    # File Storage
    # -------------------------------------------------------------------------
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 50
    allowed_extensions: list[str] = ["pdf", "docx", "txt", "md"]

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 220
    rate_limit_window: int = 60

    # -------------------------------------------------------------------------
    # Evaluation
    # -------------------------------------------------------------------------
    ragas_enabled: bool = True
    ragas_sample_rate: float = 0.1
    eval_dataset_path: str = "/app/evaluation/datasets"

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------
    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @computed_field  # type: ignore[misc]
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",")]
        return v


@lru_cache
def get_settings():
    settings = Settings()

    logger.debug(
        "SETTINGS_DEBUG",
        query_rewrite_enabled=settings.query_rewrite_enabled,
    )

    return settings
