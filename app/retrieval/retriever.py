"""Retrieval: soruya anlamca en yakın chunk'ları vektör veritabanından getirir.

RAG'in "R"si. LLM'e doğru bilgi ulaşıp ulaşmayacağı bu adıma bağlıdır:
burada kaçırılan bir chunk'ı en iyi LLM bile telafi edemez.
"""

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.vectorstore import get_vector_store


def retrieve(question: str, k: int | None = None, vector_store: Chroma | None = None) -> list[Document]:
    """Soruya anlamca en yakın `k` chunk'ı, en yakından uzağa sıralı döner.

    Her Document'in metadata'sına `score` eklenir: cosine uzaklığı
    (0 = birebir aynı anlam, büyüdükçe alakasız).
    """
    # Boş soru anlamsız bir vektör üretir; erken ve açık bir hata vermek daha iyi
    if not question.strip():
        raise ValueError("Soru boş olamaz")

    store = vector_store or get_vector_store()
    # Arka planda: soru embedding modeliyle vektöre çevrilir, Chroma HNSW indeksiyle
    # en yakın k vektörü bulur ve (Document, uzaklık) çiftleri olarak döndürür.
    results = store.similarity_search_with_score(question, k=k or get_settings().top_k)

    documents = []
    for doc, score in results:
        # Skoru metadata'ya taşı: sonraki adımlar (kaynak kartları, eval) tek bir
        # Document listesiyle çalışabilsin. 4 hane okunurluk için yeterli.
        doc.metadata["score"] = round(score, 4)
        documents.append(doc)
    return documents
