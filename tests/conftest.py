"""Shared fixtures.

Tests use the offline hashing embedder, a temporary docs folder and index, and a scripted fake
LLM, so they need no network and no API key.
"""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.llm.provider import LLMProvider
from app.main import create_app
from app.rag.service import RagService

ROOT = Path(__file__).resolve().parents[1]
REAL_DOCS = ROOT / "docs"


class ScriptedLLM(LLMProvider):
    """Plays back fixed replies and records the messages it was sent."""

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools=None):
        self.calls.append(messages)
        assert self.replies, "The LLM was called more times than the test scripted."
        return {"role": "assistant", "content": self.replies.pop(0)}


@pytest.fixture
def settings(tmp_path) -> Settings:
    docs = tmp_path / "docs"
    docs.mkdir()
    for pdf in REAL_DOCS.glob("*.pdf"):
        shutil.copy(pdf, docs)
    return Settings(
        _env_file=None,
        docs_dir=str(docs),
        index_dir=str(tmp_path / "index"),
        auto_ingest=True,
        embedding_provider="hashing",
        min_score=None,
        llm_model="",
        openrouter_api_key="",
    )


@pytest.fixture
def service(settings) -> RagService:
    """A service with the sample documents already indexed."""
    svc = RagService(settings)
    svc.ingest()
    return svc


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def api_service(client) -> RagService:
    return client.app.state.service
