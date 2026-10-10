"""Embedder interface and factory.

Switching from the offline default to real semantic embeddings is a configuration change
(EMBEDDING_PROVIDER / EMBEDDING_MODEL). The vector store records which embedder built the
index, so a change triggers a clean rebuild instead of silently comparing incompatible vectors.
"""

from abc import ABC, abstractmethod

import numpy as np

from app.config import Settings, get_settings


class EmbeddingError(Exception):
    """The embedding service failed or returned something unusable."""


class EmbeddingConfigError(EmbeddingError):
    """Embeddings are not configured correctly (missing model or API key, unknown provider)."""


class Embedder(ABC):
    #: Identifies the vector space. Vectors from different ids must never be compared.
    id: str
    #: Similarity below which a passage is treated as irrelevant, unless MIN_SCORE overrides it.
    default_min_score: float

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n, dim) float32 array of L2-normalised vectors, one row per text."""


def get_embedder(settings: Settings | None = None) -> Embedder:
    settings = settings or get_settings()
    provider = settings.embedding_provider.strip().lower()

    if provider == "hashing":
        from app.embeddings.hashing import HashingEmbedder

        return HashingEmbedder(dim=settings.hashing_dim)

    if provider in ("openrouter", "openai"):
        from app.embeddings.api import APIEmbedder

        if not settings.embedding_model:
            raise EmbeddingConfigError("EMBEDDING_MODEL is not set.")
        api_key = settings.openrouter_api_key if provider == "openrouter" else settings.openai_api_key
        if not api_key:
            raise EmbeddingConfigError(f"{provider.upper()}_API_KEY is not set.")
        default_url = (
            "https://openrouter.ai/api/v1" if provider == "openrouter" else "https://api.openai.com/v1"
        )
        return APIEmbedder(
            api_key=api_key,
            model=settings.embedding_model,
            base_url=settings.embedding_base_url or default_url,
            timeout=settings.llm_timeout_seconds,
        )

    raise EmbeddingConfigError(f"Unknown EMBEDDING_PROVIDER '{settings.embedding_provider}'.")
