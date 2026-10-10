import json
import os
import subprocess
import sys

import httpx
import numpy as np
import pytest

from app.config import Settings
from app.embeddings.api import APIEmbedder
from app.embeddings.hashing import HashingEmbedder, _stem
from app.embeddings.provider import EmbeddingConfigError, EmbeddingError, get_embedder
from tests.conftest import ROOT


def cosine(a, b) -> float:
    return float(a @ b)


# --- hashing embedder ---------------------------------------------------------------------


def test_vectors_are_unit_length_and_deterministic():
    embedder = HashingEmbedder(dim=512)
    first = embedder.embed(["annual leave entitlement", "password rules"])
    second = HashingEmbedder(dim=512).embed(["annual leave entitlement", "password rules"])

    assert first.shape == (2, 512)
    assert np.allclose(np.linalg.norm(first, axis=1), 1.0)
    assert np.array_equal(first, second)


def test_text_with_no_content_words_gives_a_zero_vector():
    vector = HashingEmbedder(dim=64).embed(["the and of to"])[0]
    assert not vector.any()


def test_shared_vocabulary_scores_higher_than_unrelated_text():
    embedder = HashingEmbedder()
    query, related, unrelated = embedder.embed(
        ["how many days of annual leave", "Employees get 21 days of annual leave per year", "Passwords must be 14 characters"]
    )
    assert cosine(query, related) > cosine(query, unrelated) + 0.2


@pytest.mark.parametrize(
    "a, b",
    [("days", "day"), ("working", "work"), ("approves", "approved"), ("leave", "leaves"), ("policies", "policy")],
)
def test_stemmer_conflates_inflections(a, b):
    assert _stem(a) == _stem(b)


def test_stemmer_leaves_short_and_special_words_alone():
    assert _stem("is") == "is"
    assert _stem("pass") == "pass"
    assert _stem("bus") == "bus"


def test_embeddings_do_not_depend_on_pythons_per_process_hash_seed():
    """Saved indexes would break if the vectors changed between runs."""
    code = (
        "import numpy as np; from app.embeddings.hashing import HashingEmbedder as H; "
        "v = H(256).embed(['annual leave days'])[0]; print(round(float(v @ np.arange(256)), 4))"
    )

    def run(seed: str) -> str:
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
        return subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout

    assert run("1") == run("2")
    assert float(run("1")) != 0.0


# --- API embedder -------------------------------------------------------------------------

VECTORS = {"a": [3.0, 0.0], "b": [0.0, 2.0], "c": [1.0, 1.0]}


def make_embedder(handler, **kwargs) -> APIEmbedder:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return APIEmbedder(api_key="test-key", model="qwen/test-embed", base_url="https://example.test/v1", client=client, **kwargs)


def echo_handler(requests: list):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append((request, body))
        data = [{"index": i, "embedding": VECTORS[text]} for i, text in enumerate(body["input"])]
        return httpx.Response(200, json={"data": list(reversed(data))})  # deliberately out of order

    return handler


def test_request_format_and_ordering():
    seen: list = []
    result = make_embedder(echo_handler(seen)).embed(["a", "b", "c"])

    request, body = seen[0]
    assert str(request.url) == "https://example.test/v1/embeddings"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert body == {"model": "qwen/test-embed", "input": ["a", "b", "c"]}
    # rows follow the order of the inputs, not the order of the response, and are normalised
    assert np.allclose(result, [[1, 0], [0, 1], [2**-0.5, 2**-0.5]])


def test_large_inputs_are_sent_in_batches():
    seen: list = []
    result = make_embedder(echo_handler(seen), batch_size=2).embed(["a", "b", "c", "a", "b"])

    assert [len(body["input"]) for _, body in seen] == [2, 2, 1]
    assert result.shape == (5, 2)


def test_no_texts_means_no_request():
    seen: list = []
    assert len(make_embedder(echo_handler(seen)).embed([])) == 0
    assert seen == []


def test_http_error_does_not_leak_the_key():
    embedder = make_embedder(lambda r: httpx.Response(401, text="bad key test-key"))
    with pytest.raises(EmbeddingError) as exc_info:
        embedder.embed(["a"])
    assert "test-key" not in str(exc_info.value)


@pytest.mark.parametrize(
    "body",
    [{"nope": 1}, {"data": []}, {"data": [{"index": 0}]}, {"data": [{"index": 0, "embedding": [1, 0]}] * 2}],
)
def test_malformed_responses_become_embedding_errors(body):
    with pytest.raises(EmbeddingError):
        make_embedder(lambda r: httpx.Response(200, json=body)).embed(["a"])


def test_network_failure_becomes_embedding_error():
    def handler(request):
        raise httpx.ConnectError("no route")

    with pytest.raises(EmbeddingError):
        make_embedder(handler).embed(["a"])


# --- factory ------------------------------------------------------------------------------


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_factory_default_is_the_offline_embedder():
    embedder = get_embedder(settings())
    assert isinstance(embedder, HashingEmbedder)
    assert embedder.id == "hashing-4096"


def test_factory_builds_openrouter_embedder():
    embedder = get_embedder(settings(embedding_provider="openrouter", embedding_model="qwen/qwen3-embedding-0.6b", openrouter_api_key="k"))
    assert isinstance(embedder, APIEmbedder)
    assert embedder.base_url == "https://openrouter.ai/api/v1"
    assert embedder.id == "api:qwen/qwen3-embedding-0.6b"


def test_factory_base_url_override():
    embedder = get_embedder(settings(embedding_provider="openai", embedding_model="m", openai_api_key="k", embedding_base_url="http://localhost:8080/v1/"))
    assert embedder.base_url == "http://localhost:8080/v1"


@pytest.mark.parametrize(
    "overrides",
    [
        {"embedding_provider": "openrouter", "embedding_model": "", "openrouter_api_key": "k"},
        {"embedding_provider": "openrouter", "embedding_model": "m", "openrouter_api_key": ""},
        {"embedding_provider": "openai", "embedding_model": "m", "openai_api_key": ""},
        {"embedding_provider": "mystery"},
    ],
)
def test_factory_rejects_bad_configuration(overrides):
    with pytest.raises(EmbeddingConfigError):
        get_embedder(settings(**overrides))
