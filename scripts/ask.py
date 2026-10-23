"""Soruyu RAG chain ile cevaplar (retrieval + Ollama).

Kullanım:
    uv run python -m scripts.ask "Yurt dışında yemek harcırahı ne kadar?"
"""

import sys
import time

from app.retrieval.rag import answer_question


def main(question: str) -> None:
    start = time.perf_counter()
    result = answer_question(question)
    print(f"CEVAP ({time.perf_counter() - start:.1f} sn):\n{result.answer}\n\nKAYNAKLAR:")
    for s in result.sources:
        print(f"  [{s.ref}] {s.source}, sayfa {s.page} (uzaklık {s.score:.3f})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
