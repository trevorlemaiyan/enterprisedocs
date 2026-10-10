import pytest

from app.embeddings.provider import EmbeddingError
from app.llm.provider import LLMError, LLMProvider
from app.rag.prompts import NO_ANSWER
from tests.conftest import ScriptedLLM

QUESTION = "How many days of annual leave do employees get?"


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["documents"] == 4 and body["chunks"] > 30


def test_web_ui_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "EnterpriseDocs AI" in response.text


def test_openapi_lists_all_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) == {"/health", "/ask", "/search", "/documents", "/documents/{name}", "/ingest"}
    assert client.get("/docs").status_code == 200


def test_list_documents(client):
    documents = client.get("/documents").json()
    assert [d["name"] for d in documents] == ["HR_Policy.pdf", "IT_Support_Guide.pdf", "Leave_Policy.pdf", "Procurement_Policy.pdf"]
    assert all(d["pages"] == 2 and d["chunks"] >= 8 and len(d["sha256"]) == 64 for d in documents)


# --- search -------------------------------------------------------------------------------


def test_search_returns_scored_results(client):
    body = client.post("/search", json={"query": QUESTION, "top_k": 3}).json()

    assert body["min_score"] == 0.10
    assert len(body["results"]) == 3
    top = body["results"][0]
    assert (top["document"], top["page"], top["section"]) == ("Leave_Policy.pdf", 1, "2. Annual Leave")
    assert top["relevant"] is True and top["score"] > 0.3
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)


def test_search_marks_irrelevant_results(client):
    results = client.post("/search", json={"query": "What is the capital of France?"}).json()["results"]
    assert results and not any(r["relevant"] for r in results)


@pytest.mark.parametrize("payload", [{"query": ""}, {}, {"query": "x", "top_k": 0}, {"query": "x", "top_k": 11}])
def test_search_validates_input(client, payload):
    assert client.post("/search", json=payload).status_code == 422


# --- ask ----------------------------------------------------------------------------------


def test_ask_returns_answer_with_sources(client, api_service):
    api_service._llm = ScriptedLLM("Employees get 21 working days of annual leave per year [1].")
    response = client.post("/ask", json={"question": QUESTION})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Employees get 21 working days of annual leave per year [1]."
    assert body["grounded"] is True
    (source,) = body["sources"]
    assert source["id"] == 1
    assert (source["document"], source["page"], source["section"]) == ("Leave_Policy.pdf", 1, "2. Annual Leave")
    assert "21 working days" in source["snippet"]


def test_ask_about_something_not_in_the_documents(client, api_service):
    api_service._llm = ScriptedLLM()  # must not be called
    body = client.post("/ask", json={"question": "Who won the 2022 football World Cup?"}).json()
    assert body == {"answer": NO_ANSWER, "grounded": False, "sources": []}


def test_long_passages_are_shortened_in_sources(client, api_service, tmp_path):
    api_service.add_upload("long.txt", ("1. Essay\n" + "Visitors must always sign in at reception. " * 40).encode())
    api_service._llm = ScriptedLLM("Sign in [1].")
    source = client.post("/ask", json={"question": "Where must visitors sign in at reception?", "top_k": 1}).json()["sources"][0]
    assert len(source["snippet"]) <= 304 and source["snippet"].endswith("...")


@pytest.mark.parametrize("payload", [{"question": ""}, {}, {"question": "x" * 1001}, {"question": "x", "top_k": 99}])
def test_ask_validates_input(client, payload):
    assert client.post("/ask", json=payload).status_code == 422


def test_llm_failure_returns_502_without_details(client, api_service):
    class BrokenLLM(LLMProvider):
        def chat(self, messages, tools=None):
            raise LLMError("upstream said: secret internals")

    api_service._llm = BrokenLLM()
    response = client.post("/ask", json={"question": QUESTION})

    assert response.status_code == 502
    assert "secret internals" not in response.text


def test_unconfigured_llm_returns_503(client):
    # The fixture settings have no LLM_MODEL / key.
    response = client.post("/ask", json={"question": QUESTION})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_search_still_works_without_an_llm(client):
    assert client.post("/search", json={"query": QUESTION}).status_code == 200


def test_embedding_failure_returns_502_without_details(client, api_service, monkeypatch):
    def fail(texts):
        raise EmbeddingError("provider said: secret key abc123")

    monkeypatch.setattr(api_service.embedder, "embed", fail)
    response = client.post("/search", json={"query": "leave"})

    assert response.status_code == 502
    assert "abc123" not in response.text


# --- documents ----------------------------------------------------------------------------


def test_upload_then_search_and_list(client):
    response = client.post("/documents", files={"file": ("parking.txt", b"1. Parking\nVisitors must register their vehicle.", "text/plain")})
    assert response.status_code == 201
    assert response.json() == {"document": "parking.txt", "chunks": 1}

    assert "parking.txt" in [d["name"] for d in client.get("/documents").json()]
    top = client.post("/search", json={"query": "register a visitor vehicle", "top_k": 1}).json()["results"][0]
    assert top["document"] == "parking.txt"


def test_upload_rejects_unsupported_type(client):
    response = client.post("/documents", files={"file": ("virus.exe", b"MZ", "application/octet-stream")})
    assert response.status_code == 415


def test_upload_rejects_empty_file(client):
    assert client.post("/documents", files={"file": ("a.txt", b"", "text/plain")}).status_code == 400


def test_upload_rejects_oversized_file(settings):
    from fastapi.testclient import TestClient
    from app.main import create_app

    settings.max_upload_mb = 1
    with TestClient(create_app(settings)) as small_client:
        response = small_client.post("/documents", files={"file": ("big.txt", b"x" * (1024 * 1024 + 5), "text/plain")})
    assert response.status_code == 413


def test_upload_of_unreadable_pdf_is_a_422(client):
    response = client.post("/documents", files={"file": ("bad.pdf", b"definitely not a pdf", "application/pdf")})
    assert response.status_code == 422
    assert "bad.pdf" not in [d["name"] for d in client.get("/documents").json()]


def test_upload_requires_a_file(client):
    assert client.post("/documents").status_code == 422


def test_delete_document(client):
    upload_res = client.post("/documents", files={"file": ("to_delete.txt", b"1. Policy\nText to delete.", "text/plain")})
    assert upload_res.status_code == 201

    del_res = client.delete("/documents/to_delete.txt")
    assert del_res.status_code == 200
    assert del_res.json() == {"document": "to_delete.txt", "deleted": True}
    assert "to_delete.txt" not in [d["name"] for d in client.get("/documents").json()]

    del_again = client.delete("/documents/to_delete.txt")
    assert del_again.status_code == 404


# --- ingest -------------------------------------------------------------------------------


def test_ingest_endpoint_reports_changes(client, api_service):
    assert len(client.post("/ingest").json()["unchanged"]) == 4

    (api_service.docs_dir / "extra.md").write_text("# Extra\nSome extra policy text.", encoding="utf-8")
    (api_service.docs_dir / "HR_Policy.pdf").unlink()
    body = client.post("/ingest").json()
    assert body["added"] == ["extra.md"] and body["removed"] == ["HR_Policy.pdf"]


def test_ingest_force(client):
    assert len(client.post("/ingest?force=true").json()["updated"]) == 4
