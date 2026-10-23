from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


def split_documents(
    documents: list[Document],
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
        chunk_overlap=chunk_overlap if chunk_overlap is not None else settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True,
    )
    chunks = splitter.split_documents(documents)

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    return chunks
