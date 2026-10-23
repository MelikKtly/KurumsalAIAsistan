from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader


def load_pdf(path: str | Path) -> list[Document]:
    """Tek bir PDF'i sayfa sayfa Document listesi olarak yükler.

    Her Document'in metadata'sında `source` (dosya yolu) ve `page` (0'dan başlayan
    sayfa numarası) bulunur; bunlar ileride cevapta kaynak göstermek için kullanılır.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF bulunamadı: {path}")

    reader = PdfReader(path)
    return [
        Document(
            page_content=page.extract_text() or "",
            metadata={"source": str(path), "page": i, "total_pages": len(reader.pages)},
        )
        for i, page in enumerate(reader.pages)
    ]


def load_pdfs(directory: str | Path) -> list[Document]:
    """Bir klasördeki tüm PDF'leri yükler."""
    documents: list[Document] = []
    for pdf in sorted(Path(directory).glob("*.pdf")):
        documents.extend(load_pdf(pdf))
    return documents
