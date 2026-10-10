"""Local, offline "embedding" using feature hashing.

Be clear about what this is: a *lexical* vector. Words (and adjacent word pairs) are hashed
into a fixed-size vector, so texts that share vocabulary are close together. It does NOT
understand meaning: "holiday" and "annual leave" are unrelated to it. It exists so the whole
project, including the tests, runs with no API key and no model download. For real semantic
search, switch to an API embedding model (see EMBEDDING_PROVIDER).
"""

import hashlib
import math
import re
from collections import Counter
from functools import lru_cache

import numpy as np

from app.embeddings.provider import Embedder

_TOKEN = re.compile(r"[a-z0-9]+")

# Words that carry little meaning on their own. Kept deliberately generic (not tuned to the sample docs).
_STOPWORDS = frozenset(
    """a an the and or but if of to in on at by for from with without as is are was were be been being
    do does did done have has had having i me my we our you your he she it its they their them this that
    these those there here what which who whom whose when where why how can could should would will shall
    may might must not no any all some more most other such than then so also into out up down over under
    about after before during per each both either neither""".split()
)


def _stem(word: str) -> str:
    """Very light suffix stripping so 'days'/'day', 'working'/'work' and 'approve'/'approved' match."""
    if len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    if len(word) > 4 and word.endswith("e"):
        word = word[:-1]
    return word


@lru_cache(maxsize=100_000)
def _bucket(feature: str, dim: int) -> tuple[int, float]:
    # blake2b, not Python's hash(): hash() is randomised per process, which would break saved indexes.
    value = int.from_bytes(hashlib.blake2b(feature.encode(), digest_size=8).digest(), "big")
    return value % dim, 1.0 if (value >> 63) & 1 else -1.0


def _features(text: str) -> Counter[str]:
    words = [_stem(w) for w in _TOKEN.findall(text.lower()) if w not in _STOPWORDS]
    features: Counter[str] = Counter(words)
    # Adjacent pairs capture short phrases like "annual leave" or "sick leave".
    features.update(f"{a}_{b}" for a, b in zip(words, words[1:]))
    return features


class HashingEmbedder(Embedder):
    # Chosen on the small eval set in data/eval_questions.json: low enough that no valid
    # question is refused, accepting that a borderline off-topic one can slip through to the
    # LLM (whose prompt tells it to refuse). Re-tune with `python -m scripts.evaluate`.
    default_min_score = 0.10

    def __init__(self, dim: int = 4096) -> None:
        self.dim = dim
        self.id = f"hashing-{dim}"

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for feature, count in _features(text).items():
                index, sign = _bucket(feature, self.dim)
                weight = 1.0 + math.log(count)
                if "_" in feature:
                    weight *= 0.7  # phrases help, but should not outweigh the words themselves
                matrix[row, index] += sign * weight
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        np.divide(matrix, norms, out=matrix, where=norms > 0)
        return matrix
