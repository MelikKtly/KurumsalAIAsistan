from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.ingestion.pipeline import ingest_pdf
from app.retrieval.rag import PROMPT, answer_question, format_context
from app.vectorstore import get_vector_store

SAMPLE_PDF = Path("data/samples/ornek_ik_el_kitabi.pdf")


@pytest.fixture
def store(tmp_path):
    store = get_vector_store(
        embeddings=DeterministicFakeEmbedding(size=64),
        persist_directory=str(tmp_path / "chroma"),
    )
    ingest_pdf(SAMPLE_PDF, store)
    return store


def fake_llm(reply: str) -> GenericFakeChatModel:
    # Gerçek LLM yerine sabit cevap dönen sahte model: hızlı, Ollama gerektirmez
    return GenericFakeChatModel(messages=iter([AIMessage(content=reply)]))


def test_format_context_numbers_chunks_with_page():
    docs = [
        Document(page_content="birinci", metadata={"source": "data/a.pdf", "page": 0}),
        Document(page_content="ikinci", metadata={"source": "data/a.pdf", "page": 2}),
    ]
    context = format_context(docs)
    assert "[1] (a.pdf, sayfa 1)\nbirinci" in context
    assert "[2] (a.pdf, sayfa 3)\nikinci" in context


def test_prompt_contains_context_and_question():
    messages = PROMPT.format_messages(context="BAĞLAM-METNİ", question="SORU-METNİ")
    assert "BAĞLAM-METNİ" in messages[0].content
    assert messages[1].content == "SORU-METNİ"


def test_answer_question_returns_answer_and_sources(store):
    result = answer_question("Yıllık izin kaç gün?", llm=fake_llm("  14 iş günü [1]  "), vector_store=store)
    assert result.answer == "14 iş günü [1]"
    assert len(result.sources) == 4
    assert [s.ref for s in result.sources] == [1, 2, 3, 4]
    assert all(s.source == "ornek_ik_el_kitabi.pdf" and s.page >= 1 for s in result.sources)
