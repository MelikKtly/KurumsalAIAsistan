"""Ingestion 2. adım: sayfaları retrieval için küçük parçalara (chunk) böler.

Neden: Bütün bir sayfa birçok konuyu karıştırır; soruyla isabetli eşleşmesi zordur.
Küçük, tek konulu parçalar hem daha iyi bulunur hem de LLM'e sadece ilgili kısım gider.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


def split_documents(
    documents: list[Document],
    # None ise .env'deki değer kullanılır; testler farklı boyutları denemek için verir
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """Document'leri retrieval için daha küçük parçalara (chunk) böler.

    Splitter önce paragraf, sonra satır, sonra cümle, en son kelime sınırından bölmeyi
    dener; böylece parçalar mümkün olduğunca anlamlı kalır. Her chunk, kaynak
    Document'in metadata'sını (source, page) korur ve ek olarak `chunk_id` ile
    sayfa içindeki konumunu (`start_index`) taşır.
    """
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        # `or` yerine açık None kontrolü: overlap=0 geçerli bir değer, `0 or 150` → 150 olurdu
        chunk_overlap=chunk_overlap if chunk_overlap is not None else settings.chunk_overlap,
        # Bölme noktası tercih sırası: paragraf → satır → cümle sonu → kelime → (son çare) karakter.
        # Parça chunk_size'ı aşıyorsa bir sonraki ayraçla tekrar denenir ("recursive").
        separators=["\n\n", "\n", ". ", " ", ""],
        # Her chunk'ın sayfa içindeki başlangıç karakterini metadata'ya yaz
        # (sabit ID üretmek ve örtüşmeyi test etmek için kullanılıyor)
        add_start_index=True,
    )
    # Metadata (source, page) her chunk'a otomatik kopyalanır
    chunks = splitter.split_documents(documents)

    # Tüm chunk'lara 0'dan başlayan sıra numarası ver (raporlarda/arayüzde kolay referans)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    return chunks
