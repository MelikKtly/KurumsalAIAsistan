import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.agent.tools as tools_module
from app.api.main import agent_llm_dependency, app, llm_dependency, vector_store_dependency
from app.config import get_settings
from app.db import QueryLog, get_engine
from app.ingestion.pipeline import ingest_pdf
from app.retrieval.rag import get_rag_prompt
from app.vectorstore import get_vector_store
from tests.fakes import ScriptedToolModel, tool_call

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
    # `with` bloğu uygulamanın lifespan'ini çalıştırır → init_db() tabloları oluşturur
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def saved_queries() -> list[QueryLog]:
    with Session(get_engine()) as session:
        return list(session.scalars(select(QueryLog).order_by(QueryLog.id)))


def test_ask_returns_answer_with_sources(client):
    response = client.post("/ask", json={"question": "Yurt dışı harcırah ne kadar?"})
    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "Yurt dışı harcırah ne kadar?"
    assert body["answer"] == "75 Euro [1]"
    assert len(body["sources"]) == 4
    assert set(body["sources"][0]) == {"ref", "source", "page", "chunk_id", "score", "snippet", "cited"}
    assert body["answer_type"] == "answered"
    assert [src["cited"] for src in body["sources"]] == [True, False, False, False]


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "   "}, {"question": "x" * 1001}])
def test_ask_rejects_invalid_question(client, payload):
    assert client.post("/ask", json=payload).status_code == 422


def test_ask_not_found_marks_no_source_as_cited(client):
    not_found = get_rag_prompt().fixed_replies["not_found"]
    app.dependency_overrides[llm_dependency] = lambda: GenericFakeChatModel(
        messages=iter([AIMessage(content=not_found)])
    )
    body = client.post("/ask", json={"question": "Şirketin CEO'su kim?"}).json()
    assert body["answer_type"] == "not_found"
    assert not any(src["cited"] for src in body["sources"])


def test_ask_returns_metrics_and_writes_log(client):
    body = client.post("/ask", json={"question": "Yurt dışı harcırah?"}).json()
    m = body["metrics"]
    # Her adımın süresi ölçülmüş olmalı; hakem testlerde kapalı → grounding yok
    assert m["retrieval_ms"] >= 0 and m["generation_ms"] >= 0 and m["total_ms"] >= m["generation_ms"]
    assert m["grounding_ms"] is None and m["grounding_tokens"] is None

    # Log dosyasına tam bir JSON satırı eklenmiş olmalı
    lines = open(get_settings().request_log_path, encoding="utf-8").read().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["status"] == "ok" and record["question"] == "Yurt dışı harcırah?"
    assert record["metrics"]["total_ms"] == m["total_ms"]
    assert "timestamp" in record


def test_ask_returns_503_when_llm_unreachable(client):
    class DownLLM(GenericFakeChatModel):
        def _generate(self, *args, **kwargs):
            raise httpx.ConnectError("Connection refused")

    app.dependency_overrides[llm_dependency] = lambda: DownLLM(messages=iter([]))
    response = client.post("/ask", json={"question": "izin"})
    assert response.status_code == 503
    # Hata da loglanmalı
    record = open(get_settings().request_log_path, encoding="utf-8").read().splitlines()[-1]
    assert '"status": "error"' in record


def test_index_serves_chat_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Kurumsal AI Asistanı" in response.text


def test_ask_is_saved_to_database(client):
    client.post("/ask", json={"question": "Yurt dışı harcırah?"})
    [row] = saved_queries()
    assert (row.endpoint, row.status, row.question) == ("ask", "ok", "Yurt dışı harcırah?")
    assert row.answer == "75 Euro [1]" and row.answer_type == "answered"


def test_agent_endpoint_runs_tools_and_saves_history(client, monkeypatch):
    model = ScriptedToolModel([
        AIMessage(content="", tool_calls=[tool_call("get_exchange_rate", {"base": "EUR"})]),
        AIMessage(content="1 EUR = 50 TL"),
    ])
    app.dependency_overrides[agent_llm_dependency] = lambda: model
    # Gerçek kur servisine gitmesin: aracın içindeki fonksiyonu sahtesiyle değiştir (test bitince geri alınır)
    monkeypatch.setattr(tools_module.get_exchange_rate, "func", lambda base, target="TRY": f"1 {base} = 50 {target}")

    body = client.post("/agent", json={"question": "Euro kaç TL?"}).json()
    assert body["answer"] == "1 EUR = 50 TL"
    assert [s["tool"] for s in body["steps"]] == ["get_exchange_rate"]
    assert body["cost_usd"] == 0  # lokal model
    [row] = saved_queries()
    assert row.endpoint == "agent" and row.tools_used == ["get_exchange_rate"] and row.llm_calls == 2


def test_responses_carry_request_id(client):
    response = client.get("/health")
    # Middleware her cevaba benzersiz bir istek kimliği ekler (loglarda aynı id ile aranabilir)
    assert len(response.headers["X-Request-ID"]) == 12
