"""Cevap metnindeki [n] atıflarını ayrıştırma.

Hem RAG cevabının sınıflandırılmasında (rag.py) hem de değerlendirmede
(evaluation/scoring.py) kullanılır; ikisinin aynı kuralı uygulaması için tek yerde.
"""

import re

# Köşeli parantez içindeki atıfları yakalar: "[1]", "[K1]", "[12]"...
# [^\[\]]{1,10}: içinde köşeli parantez olmayan 1–10 karakter → geçersiz atıfları da yakalayabilmek için
# sadece rakam aramıyoruz. Parantez içi () grubu findall'un sadece içeriği ("1", "K1") döndürmesini sağlar.
CITATION = re.compile(r"\[([^\[\]]{1,10})\]")


def extract_citations(answer: str) -> list[str]:
    """Cevaptaki tüm atıf içerikleri, örn. "75 Euro [1], [K1]" → ["1", "K1"]."""
    return CITATION.findall(answer)


def valid_refs(citations: list[str], n_sources: int) -> set[int]:
    """Geçerli atıf numaraları: 1..n_sources aralığındaki tam sayılar.

    Örn. 4 kaynak varken ["1", "K1", "7", "1"] → {1}  ("K1" sayı değil, 7 aralık dışı).
    """
    return {int(c) for c in citations if c.isdigit() and 1 <= int(c) <= n_sources}
