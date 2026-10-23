from pathlib import Path

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.ingestion.chunker import split_documents
from app.ingestion.loader import load_pdf
from app.ingestion.pipeline import ingest_pdf
from app.retrieval.retriever import retrieve
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


def test_returns_k_documents_with_scores(store):
    docs = retrieve("yıllık izin", k=3, vector_store=store)
    assert len(docs) == 3
    assert all("score" in d.metadata for d in docs)


def test_results_sorted_by_distance(store):
    scores = [d.metadata["score"] for d in retrieve("masraf", k=5, vector_store=store)]
    assert scores == sorted(scores)


def test_exact_chunk_text_ranks_first(store):
    # Sahte embedding'de aynı metin aynı vektörü üretir → uzaklık 0
    target = split_documents(load_pdf(SAMPLE_PDF))[3]
    top = retrieve(target.page_content, k=1, vector_store=store)[0]
    assert top.metadata["chunk_id"] == target.metadata["chunk_id"]
    assert top.metadata["score"] == pytest.approx(0, abs=1e-3)


def test_empty_question_rejected(store):
    with pytest.raises(ValueError):
        retrieve("   ", vector_store=store)
