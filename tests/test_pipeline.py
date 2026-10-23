from pathlib import Path

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.ingestion.chunker import split_documents
from app.ingestion.loader import load_pdf
from app.ingestion.pipeline import chunk_id, ingest_pdf
from app.vectorstore import get_vector_store

SAMPLE_PDF = Path("data/samples/ornek_ik_el_kitabi.pdf")


@pytest.fixture
def store(tmp_path):
    # Gerçek model yerine sahte embedding: hızlı, indirme gerektirmez
    return get_vector_store(
        embeddings=DeterministicFakeEmbedding(size=64),
        persist_directory=str(tmp_path / "chroma"),
    )


def test_ingest_writes_all_chunks(store):
    written = ingest_pdf(SAMPLE_PDF, store)
    assert written == len(split_documents(load_pdf(SAMPLE_PDF)))
    assert store._collection.count() == written


def test_ingest_is_idempotent(store):
    first = ingest_pdf(SAMPLE_PDF, store)
    ingest_pdf(SAMPLE_PDF, store)
    assert store._collection.count() == first


def test_stored_chunks_keep_metadata(store):
    ingest_pdf(SAMPLE_PDF, store)
    stored = store.get(include=["metadatas"])["metadatas"]
    assert {m["page"] for m in stored} == {0, 1, 2}
    assert all(m["source"].endswith("ornek_ik_el_kitabi.pdf") for m in stored)


def test_chunk_ids_are_unique_and_stable():
    chunks = split_documents(load_pdf(SAMPLE_PDF))
    ids = [chunk_id(c) for c in chunks]
    assert len(set(ids)) == len(ids)
    assert ids == [chunk_id(c) for c in split_documents(load_pdf(SAMPLE_PDF))]
