import hashlib
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.ingestion.chunker import split_documents
from app.ingestion.loader import load_pdf
from app.vectorstore import get_vector_store


def chunk_id(chunk: Document) -> str:
    """Chunk için kaynak, sayfa ve konumdan türetilen sabit ID.

    Aynı PDF tekrar yüklendiğinde aynı ID'ler üretilir; Chroma bu ID'lerin üzerine
    yazar, böylece kopya kayıt oluşmaz.
    """
    m = chunk.metadata
    key = f"{m['source']}:{m['page']}:{m['start_index']}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def ingest_pdf(path: str | Path, vector_store: Chroma | None = None) -> int:
    """PDF'i yükler, parçalara böler ve Chroma'ya yazar. Yazılan chunk sayısını döner."""
    store = vector_store or get_vector_store()
    chunks = split_documents(load_pdf(path))
    if chunks:
        store.add_documents(chunks, ids=[chunk_id(c) for c in chunks])
    return len(chunks)
