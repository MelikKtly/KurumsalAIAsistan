"""Chroma'da anlamsal arama yapar (LLM olmadan, sadece retrieval).

Retrieval'ın doğru chunk'ı bulup bulmadığını LLM'den bağımsız görmek için kullanışlı.

Kullanım:
    uv run python -m scripts.search "Yurt dışında yemek harcırahı ne kadar?"
"""

import sys

from app.retrieval.retriever import retrieve


def main(question: str) -> None:
    # retrieve() en yakından uzağa sıralı döner; rank 1'den başlasın
    for rank, doc in enumerate(retrieve(question), start=1):
        m = doc.metadata
        print(f"#{rank}  uzaklık={m['score']:.3f}  sayfa={m['page'] + 1}  chunk={m['chunk_id']}")
        # İlk 150 karakter, satır sonları tek satırda okunacak şekilde boşluğa çevrilmiş
        print("    " + doc.page_content[:150].replace("\n", " ") + "...")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
