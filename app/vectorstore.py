"""Vektör veritabanı (Chroma) bağlantısı.

Chroma'ya erişim yalnızca bu dosyadan yapılır. İleride Chroma sunucu moduna,
Qdrant'a veya pgvector'a geçilirse sadece burası değişir; ingestion ve retrieval
kodu aynı kalır.
"""

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
    """Diskte kalıcı Chroma koleksiyonuna bağlanır (yoksa oluşturur)."""
    settings = get_settings()
    return Chroma(
        collection_name=settings.chroma_collection,
        # Chroma'ya eklenen metinler ve sorular bu fonksiyonla vektöre çevrilir
        embedding_function=embeddings or get_embeddings(),
        # Gömülü (embedded) mod: ayrı sunucu yok, veri doğrudan bu klasöre yazılır
        # (chroma.sqlite3 = metin + metadata, UUID'li klasör = vektörler + HNSW indeksi)
        persist_directory=persist_directory or settings.chroma_dir,
        # Benzerlik ölçüsü: cosine. Arama sonucundaki skor "cosine uzaklığı" olur
        # (0 = aynı anlam, büyüdükçe alakasız). Sadece koleksiyon ilk oluşturulurken uygulanır.
        collection_metadata={"hnsw:space": "cosine"},
    )
