"""Ingestion hattı: PDF → sayfalar → chunk'lar → (embedding) → Chroma.

loader ve chunker'ı birleştirir. Embedding ayrıca çağrılmaz: Chroma'ya
`add_documents` ile metin eklenirken, vectorstore'a verilen embedding modeli
her chunk'ı otomatik olarak vektöre çevirir.
"""

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
    # Bir chunk'ı benzersiz tanımlayan bilgi: hangi dosya, hangi sayfa, sayfanın kaçıncı karakteri
    key = f"{m['source']}:{m['page']}:{m['start_index']}"
    # SHA-256 özeti: aynı girdi → her zaman aynı çıktı. İlk 32 karakter ID için yeterince benzersiz.
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def ingest_pdf(path: str | Path, vector_store: Chroma | None = None) -> int:
    """PDF'i yükler, parçalara böler ve Chroma'ya yazar. Yazılan chunk sayısını döner."""
    # Testler geçici bir store verir; normalde .env'deki kalıcı Chroma kullanılır
    store = vector_store or get_vector_store()
    chunks = split_documents(load_pdf(path))
    if chunks:  # Boş/okunamayan PDF'te Chroma'ya boş liste gönderme
        # ids verildiği için aynı ID'li kayıt varsa üzerine yazılır (upsert davranışı)
        store.add_documents(chunks, ids=[chunk_id(c) for c in chunks])
    return len(chunks)
