"""Semantic embeddings from an OpenAI-style /embeddings endpoint (OpenRouter, OpenAI, ...)."""

import logging

import httpx
import numpy as np

from app.embeddings.provider import Embedder, EmbeddingError

logger = logging.getLogger(__name__)


class APIEmbedder(Embedder):
    # A starting point only: cosine scores differ between embedding models.
    # Tune with `python -m scripts.evaluate` and set MIN_SCORE.
    default_min_score = 0.30

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 60.0,
        batch_size: int = 64,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size
        self.id = f"api:{model}"
        self._client = client or httpx.Client(timeout=timeout)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        batches = [self._embed_batch(texts[i : i + self.batch_size]) for i in range(0, len(texts), self.batch_size)]
        matrix = np.vstack(batches).astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        np.divide(matrix, norms, out=matrix, where=norms > 0)
        return matrix

    def _embed_batch(self, batch: list[str]) -> np.ndarray:
        try:
            response = self._client.post(
                f"{self.base_url}/embeddings",
                json={"model": self.model, "input": batch},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Request to embedding service failed: {type(exc).__name__}") from exc

        if response.status_code >= 400:
            # The provider's explanation goes to the log only, never into an error shown to clients.
            logger.error("Embedding API error %s: %s", response.status_code, response.text[:500])
            raise EmbeddingError(f"Embedding API returned HTTP {response.status_code}")

        try:
            items = response.json()["data"]
            items = sorted(items, key=lambda item: item.get("index", 0))
            vectors = [item["embedding"] for item in items]
            if len(vectors) != len(batch):
                raise ValueError("wrong number of embeddings")
            return np.asarray(vectors, dtype=np.float32)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise EmbeddingError("Embedding API returned a malformed response") from exc
