"""PDF'leri Chroma'ya yükler.

Kullanım:
    uv run python -m scripts.ingest data/samples/ornek_ik_el_kitabi.pdf
    uv run python -m scripts.ingest data/pdfs/          # klasördeki tüm PDF'ler
"""

import sys
from pathlib import Path

from app.ingestion.pipeline import ingest_pdf
from app.vectorstore import get_vector_store


def main(target: str) -> None:
    path = Path(target)
    # Klasör verildiyse içindeki tüm PDF'ler, dosya verildiyse sadece o
    pdfs = sorted(path.glob("*.pdf")) if path.is_dir() else [path]
    # Store bir kez oluşturulup tüm PDF'ler için paylaşılır (embedding modeli bir kez yüklenir)
    store = get_vector_store()
    for pdf in pdfs:
        print(f"{pdf}: {ingest_pdf(pdf, store)} chunk yazıldı")
    # _collection: LangChain'in sarmaladığı ham Chroma koleksiyonu; count() toplam kayıt sayısı.
    # Aynı PDF tekrar yüklendiğinde bu sayının artmaması, kopya oluşmadığını gösterir.
    print(f"Koleksiyondaki toplam chunk: {store._collection.count()}")


# Dosya `python -m scripts.ingest` ile doğrudan çalıştırıldığında burası çalışır
# (başka bir modülden import edildiğinde çalışmaz)
if __name__ == "__main__":
    # sys.argv[0] script adı, [1] kullanıcının verdiği yol. Argüman yoksa kullanım bilgisini göster.
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
