from pathlib import Path

import pytest
from langchain_core.documents import Document

from app.ingestion.chunker import split_documents
from app.ingestion.loader import load_pdf

SAMPLE_PDF = Path("data/samples/ornek_ik_el_kitabi.pdf")


@pytest.fixture(scope="module")
def pages() -> list[Document]:
    return load_pdf(SAMPLE_PDF)


def test_chunks_respect_size_limit(pages):
    chunks = split_documents(pages, chunk_size=300, chunk_overlap=50)
    assert len(chunks) > len(pages)
    assert all(len(c.page_content) <= 300 for c in chunks)


def test_chunks_keep_source_metadata(pages):
    chunks = split_documents(pages)
    assert {c.metadata["page"] for c in chunks} == {0, 1, 2}
    assert all(c.metadata["source"].endswith("ornek_ik_el_kitabi.pdf") for c in chunks)
    assert all("start_index" in c.metadata for c in chunks)


def test_chunk_ids_are_sequential(pages):
    chunks = split_documents(pages)
    assert [c.metadata["chunk_id"] for c in chunks] == list(range(len(chunks)))


def test_consecutive_chunks_overlap():
    text = " ".join(f"kelime{i}" for i in range(200))
    chunks = split_documents([Document(page_content=text)], chunk_size=200, chunk_overlap=50)
    first_end = chunks[0].metadata["start_index"] + len(chunks[0].page_content)
    assert chunks[1].metadata["start_index"] < first_end


def test_no_information_lost(pages):
    chunks = split_documents(pages)
    joined = " ".join(c.page_content for c in chunks)
    for fact in ["14 iş günü", "75 Euro", "1.500 TL", "guvenlik@ornekteknoloji.com"]:
        assert fact in joined
