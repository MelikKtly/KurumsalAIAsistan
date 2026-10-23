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
    pdfs = sorted(path.glob("*.pdf")) if path.is_dir() else [path]
    store = get_vector_store()
    for pdf in pdfs:
        print(f"{pdf}: {ingest_pdf(pdf, store)} chunk yazıldı")
    print(f"Koleksiyondaki toplam chunk: {store._collection.count()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
