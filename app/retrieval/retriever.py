from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.vectorstore import get_vector_store


def retrieve(question: str, k: int | None = None, vector_store: Chroma | None = None) -> list[Document]:
    """Soruya anlamca en yakın `k` chunk'ı, en yakından uzağa sıralı döner.

    Her Document'in metadata'sına `score` eklenir: cosine uzaklığı
    (0 = birebir aynı anlam, büyüdükçe alakasız).
    """
    if not question.strip():
        raise ValueError("Soru boş olamaz")

    store = vector_store or get_vector_store()
    results = store.similarity_search_with_score(question, k=k or get_settings().top_k)

    documents = []
    for doc, score in results:
        doc.metadata["score"] = round(score, 4)
        documents.append(doc)
    return documents
