"""Application settings, loaded from environment variables (and a local .env file)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Paths
    docs_dir: str = "docs"
    index_dir: str = "data/index"
    auto_ingest: bool = True
    max_upload_mb: int = 10

    # Chunking (characters)
    chunk_size: int = 900
    chunk_overlap: int = 150

    # Retrieval
    top_k: int = 4
    min_score: float | None = None  # None = use the embedder's default

    # Embeddings
    embedding_provider: str = "hashing"
    embedding_model: str = ""
    embedding_base_url: str = ""
    hashing_dim: int = 4096

    # Answer generation
    llm_provider: str = "openrouter"
    llm_model: str = ""
    openrouter_api_key: str = ""
    openai_api_key: str = ""
    llm_timeout_seconds: float = 60.0

    @field_validator("min_score", mode="before")
    @classmethod
    def _blank_is_none(cls, value):
        # `MIN_SCORE=` in .env arrives as an empty string.
        return None if value in ("", None) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
