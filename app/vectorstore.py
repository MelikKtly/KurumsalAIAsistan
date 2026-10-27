"""Vektör veritabanı (Chroma) bağlantısı.

Chroma'ya erişim yalnızca bu dosyadan yapılır. İki mod (Faz 4.7):
  - Gömülü (varsayılan, lokal geliştirme): Chroma uygulamanın içinde çalışır, veri chroma_dir'e yazılır
  - Sunucu (Docker Compose): CHROMA_HOST verilirse ayrı bir Chroma sunucusuna HTTP ile bağlanılır
İngestion ve retrieval kodu iki modda da aynıdır; değişen yalnızca bu dosya.
"""

import chromadb
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from app.config import get_settings
from app.embeddings import get_embeddings


def get_vector_store(
    # Parametreler opsiyonel: normalde .env ayarları kullanılır, testler ise
    # sahte embedding ve geçici bir klasör vererek gerçek veritabanına dokunmaz.
    embeddings: Embeddings | None = None,
    persist_directory: str | None = None,
) -> Chroma:
    """Chroma koleksiyonuna bağlanır (yoksa oluşturur): CHROMA_HOST varsa sunucuya, yoksa diskteki gömülü veritabanına."""
    settings = get_settings()
    # Sunucu modu: testler persist_directory verdiğinde her zaman gömülü mod kullanılır
    client = None
    if settings.chroma_host and persist_directory is None:
        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return Chroma(
        client=client,  # None → gömülü mod (persist_directory kullanılır)
        collection_name=settings.chroma_collection,
        # Chroma'ya eklenen metinler ve sorular bu fonksiyonla vektöre çevrilir
        embedding_function=embeddings or get_embeddings(),
        # Gömülü (embedded) mod: ayrı sunucu yok, veri doğrudan bu klasöre yazılır
        # (chroma.sqlite3 = metin + metadata, UUID'li klasör = vektörler + HNSW indeksi)
        persist_directory=None if client else (persist_directory or settings.chroma_dir),
        # Benzerlik ölçüsü: cosine. Arama sonucundaki skor "cosine uzaklığı" olur
        # (0 = aynı anlam, büyüdükçe alakasız). Sadece koleksiyon ilk oluşturulurken uygulanır.
        collection_metadata={"hnsw:space": "cosine"},
    )
