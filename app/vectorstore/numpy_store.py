"""A small persistent vector store: one NumPy matrix plus chunk metadata.

Vectors are L2-normalised, so cosine similarity is a single matrix-vector product. That is
exact (not approximate) and fast for tens of thousands of chunks, which is plenty for a
company policy library. For millions of chunks you would swap this class for pgvector, Qdrant
or similar behind the same few methods.

Persistence: `vectors.npy` + `index.json` in the index directory, written atomically.
"""

import json
import logging
import os
import threading
from dataclasses import asdict
from pathlib import Path

import numpy as np

from app.domain import Chunk, Hit

logger = logging.getLogger(__name__)


class NumpyVectorStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory
        self.embedder_id: str | None = None
        self._lock = threading.RLock()
        self._chunks: list[Chunk] = []
        self._vectors: np.ndarray | None = None
        self._documents: dict[str, dict] = {}

    def __len__(self) -> int:
        return len(self._chunks)

    # --- reading ---------------------------------------------------------------------

    def documents(self) -> dict[str, dict]:
        """name -> {sha256, pages, chunks}"""
        with self._lock:
            return {name: dict(info) for name, info in self._documents.items()}

    def search(self, query: np.ndarray, k: int) -> list[Hit]:
        with self._lock:
            if self._vectors is None or not self._chunks:
                return []
            if query.shape != (self._vectors.shape[1],):
                raise ValueError("Query vector does not match the index dimension.")
            scores = self._vectors @ query
            order = np.argsort(-scores)[:k]
            return [Hit(self._chunks[i], float(scores[i])) for i in order]

    # --- writing ---------------------------------------------------------------------

    def replace_document(
        self, name: str, sha256: str, pages: int, chunks: list[Chunk], vectors: np.ndarray
    ) -> None:
        """Atomically (in memory, then on disk) replace everything stored for one document."""
        if len(chunks) != len(vectors):
            raise ValueError("Each chunk needs exactly one vector.")
        with self._lock:
            self._drop(name)
            if chunks:
                self._chunks.extend(chunks)
                self._vectors = vectors if self._vectors is None else np.vstack([self._vectors, vectors])
            self._documents[name] = {"sha256": sha256, "pages": pages, "chunks": len(chunks)}
            self.save()

    def remove_document(self, name: str) -> bool:
        with self._lock:
            existed = self._drop(name)
            if existed:
                self.save()
            return existed

    def clear(self) -> None:
        with self._lock:
            self._chunks, self._vectors, self._documents = [], None, {}
            self.save()

    def _drop(self, name: str) -> bool:
        existed = name in self._documents
        self._documents.pop(name, None)
        if self._vectors is not None and self._chunks:
            keep = np.array([c.document != name for c in self._chunks])
            self._chunks = [c for c, k in zip(self._chunks, keep) if k]
            self._vectors = self._vectors[keep] if self._chunks else None
        return existed

    # --- persistence -----------------------------------------------------------------

    def save(self) -> None:
        if self.directory is None:
            return
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            meta = {
                "embedder_id": self.embedder_id,
                "documents": self._documents,
                "chunks": [asdict(c) for c in self._chunks],
            }
            _atomic_write(self.directory / "index.json", lambda f: f.write(json.dumps(meta).encode()))
            vectors = self._vectors if self._vectors is not None else np.zeros((0, 0), dtype=np.float32)
            _atomic_write(self.directory / "vectors.npy", lambda f: np.save(f, vectors))

    def load(self) -> None:
        """Load a saved index. A missing or inconsistent index just means starting empty."""
        if self.directory is None:
            return
        meta_path, vectors_path = self.directory / "index.json", self.directory / "vectors.npy"
        if not (meta_path.exists() and vectors_path.exists()):
            return
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            vectors = np.load(vectors_path, allow_pickle=False)
            chunks = [Chunk(**c) for c in meta["chunks"]]
            if len(chunks) != len(vectors):
                raise ValueError("chunk and vector counts differ")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Ignoring unreadable index in %s (%s); it will be rebuilt.", self.directory, exc)
            return
        with self._lock:
            self.embedder_id = meta.get("embedder_id")
            self._documents = meta["documents"]
            self._chunks = chunks
            self._vectors = vectors.astype(np.float32) if len(chunks) else None


def _atomic_write(path: Path, write) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "wb") as handle:
        write(handle)
    os.replace(temporary, path)
