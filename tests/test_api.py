from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.api.main import app, llm_dependency, vector_store_dependency
from app.ingestion.pipeline import ingest_pdf
from app.vectorstore import get_vector_store

SAMPLE_PDF = Path("data/samples/ornek_ik_el_kitabi.pdf")


@pytest.fixture
def client(tmp_path):
    store = get_vector_store(
        embeddings=DeterministicFakeEmbedding(size=64),
        persist_directory=str(tmp_path / "chroma"),
    )
    ingest_pdf(SAMPLE_PDF, store)

    # Gerçek Ollama ve embedding modeli yerine sahteleri enjekte et
    app.dependency_overrides[vector_store_dependency] = lambda: store
    app.dependency_overrides[llm_dependency] = lambda: GenericFakeChatModel(
        messages=iter([AIMessage(content="75 Euro [1]")])
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_ask_returns_answer_with_sources(client):
    response = client.post("/ask", json={"question": "Yurt dışı harcırah ne kadar?"})
    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "Yurt dışı harcırah ne kadar?"
    assert body["answer"] == "75 Euro [1]"
    assert len(body["sources"]) == 4
    assert set(body["sources"][0]) == {"ref", "source", "page", "chunk_id", "score", "snippet"}


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "   "}, {"question": "x" * 1001}])
def test_ask_rejects_invalid_question(client, payload):
    assert client.post("/ask", json=payload).status_code == 422


def test_ask_returns_503_when_llm_unreachable(client):
    class DownLLM(GenericFakeChatModel):
        def _generate(self, *args, **kwargs):
            raise httpx.ConnectError("Connection refused")

    app.dependency_overrides[llm_dependency] = lambda: DownLLM(messages=iter([]))
    response = client.post("/ask", json={"question": "izin"})
    assert response.status_code == 503


def test_index_serves_chat_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Kurumsal AI Asistanı" in response.text
