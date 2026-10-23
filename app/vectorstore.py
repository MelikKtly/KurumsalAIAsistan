from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from app.config import get_settings
from app.embeddings import get_embeddings


def get_vector_store(
    embeddings: Embeddings | None = None,
    persist_directory: str | None = None,
) -> Chroma:
    """Diskte kalıcı Chroma koleksiyonuna bağlanır (yoksa oluşturur)."""
    settings = get_settings()
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=embeddings or get_embeddings(),
        persist_directory=persist_directory or settings.chroma_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )
