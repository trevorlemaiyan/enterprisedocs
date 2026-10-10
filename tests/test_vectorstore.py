import numpy as np
import pytest

from app.domain import Chunk
from app.vectorstore.numpy_store import NumpyVectorStore


def chunks_for(document: str, count: int) -> list[Chunk]:
    return [Chunk(f"{document}-{i}", document, 1, "1. S", f"text {i}", i) for i in range(count)]


def unit(*values: float) -> np.ndarray:
    vector = np.array(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


@pytest.fixture
def store() -> NumpyVectorStore:
    store = NumpyVectorStore()
    store.replace_document("a.txt", "sha-a", 1, chunks_for("a.txt", 2), np.stack([unit(1, 0, 0), unit(0, 1, 0)]))
    store.replace_document("b.txt", "sha-b", 3, chunks_for("b.txt", 1), np.stack([unit(0, 0, 1)]))
    return store


def test_search_returns_best_first(store):
    hits = store.search(unit(1, 0.2, 0), k=3)
    assert [h.chunk.id for h in hits] == ["a.txt-0", "a.txt-1", "b.txt-0"]
    assert hits[0].score > hits[1].score > hits[2].score
    assert hits[0].score == pytest.approx(0.9806, abs=1e-3)


def test_k_limits_results(store):
    assert len(store.search(unit(1, 1, 1), k=2)) == 2
    assert len(store.search(unit(1, 1, 1), k=10)) == 3


def test_empty_store_returns_nothing():
    assert NumpyVectorStore().search(unit(1, 0), k=3) == []


def test_documents_summary(store):
    assert store.documents() == {
        "a.txt": {"sha256": "sha-a", "pages": 1, "chunks": 2},
        "b.txt": {"sha256": "sha-b", "pages": 3, "chunks": 1},
    }
    assert len(store) == 3


def test_replacing_a_document_removes_its_old_chunks(store):
    store.replace_document("a.txt", "sha-a2", 1, chunks_for("a.txt", 1), np.stack([unit(1, 1, 0)]))

    assert len(store) == 2
    assert store.documents()["a.txt"]["sha256"] == "sha-a2"
    assert {h.chunk.id for h in store.search(unit(1, 0, 0), k=5)} == {"a.txt-0", "b.txt-0"}


def test_remove_document(store):
    assert store.remove_document("a.txt") is True
    assert store.remove_document("a.txt") is False
    assert [h.chunk.document for h in store.search(unit(1, 1, 1), k=5)] == ["b.txt"]
    store.remove_document("b.txt")
    assert len(store) == 0 and store.search(unit(1, 1, 1), k=5) == []


def test_dimension_mismatch_is_rejected(store):
    with pytest.raises(ValueError):
        store.search(unit(1, 0), k=1)


def test_each_chunk_needs_a_vector():
    with pytest.raises(ValueError):
        NumpyVectorStore().replace_document("a.txt", "s", 1, chunks_for("a.txt", 2), np.stack([unit(1, 0)]))


def test_save_and_load_round_trip(tmp_path):
    original = NumpyVectorStore(tmp_path)
    original.embedder_id = "test-embedder"
    original.replace_document("a.txt", "sha-a", 2, chunks_for("a.txt", 2), np.stack([unit(1, 0), unit(0, 1)]))

    restored = NumpyVectorStore(tmp_path)
    restored.load()

    assert restored.embedder_id == "test-embedder"
    assert restored.documents() == original.documents()
    assert [h.chunk.id for h in restored.search(unit(0, 1), k=2)] == ["a.txt-1", "a.txt-0"]


def test_unreadable_index_means_starting_empty(tmp_path):
    (tmp_path / "index.json").write_text("{ not json", encoding="utf-8")
    np.save(tmp_path / "vectors.npy", np.zeros((0, 0), dtype=np.float32))

    store = NumpyVectorStore(tmp_path)
    store.load()
    assert len(store) == 0


def test_index_with_mismatched_counts_is_ignored(tmp_path):
    original = NumpyVectorStore(tmp_path)
    original.replace_document("a.txt", "s", 1, chunks_for("a.txt", 2), np.stack([unit(1, 0), unit(0, 1)]))
    np.save(tmp_path / "vectors.npy", np.stack([unit(1, 0)]))  # one vector too few

    restored = NumpyVectorStore(tmp_path)
    restored.load()
    assert len(restored) == 0


def test_loading_a_missing_index_is_fine(tmp_path):
    store = NumpyVectorStore(tmp_path / "nothing-here")
    store.load()
    assert len(store) == 0
