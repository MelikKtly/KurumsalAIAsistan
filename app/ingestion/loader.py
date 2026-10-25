"""Ingestion 1. adım: PDF dosyalarını okuyup LangChain Document'lerine çevirir.

Document, LangChain'in standart veri birimidir: `page_content` (metin) +
`metadata` (metinle ilgili bilgiler: kaynak dosya, sayfa no...). Sonraki tüm
adımlar (chunking, embedding, retrieval) bu yapı üzerinde çalışır.
"""

from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader


def load_pdf(path: str | Path) -> list[Document]:
    """Tek bir PDF'i sayfa sayfa Document listesi olarak yükler.

    Her Document'in metadata'sında `source` (dosya yolu) ve `page` (0'dan başlayan
    sayfa numarası) bulunur; bunlar ileride cevapta kaynak göstermek için kullanılır.
    """
    # str da gelse Path'e çevir; dosya işlemleri için daha güvenli ve okunaklı
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF bulunamadı: {path}")

    reader = PdfReader(path)
    # Her sayfa için ayrı bir Document: sayfa numarası metadata'da kalsın ki
    # cevapta "kaynak: sayfa 2" diyebilelim.
    return [
        Document(
            # extract_text() taranmış (resim) sayfalarda None dönebilir → boş metin
            page_content=page.extract_text() or "",
            metadata={"source": str(path), "page": i, "total_pages": len(reader.pages)},
        )
        for i, page in enumerate(reader.pages)  # i: 0'dan başlayan sayfa indeksi
    ]


def load_pdfs(directory: str | Path) -> list[Document]:
    """Bir klasördeki tüm PDF'leri yükler."""
    documents: list[Document] = []
    # sorted: dosyalar her çalıştırmada aynı sırayla işlensin (tekrarlanabilirlik)
    for pdf in sorted(Path(directory).glob("*.pdf")):
        documents.extend(load_pdf(pdf))
    return documents
