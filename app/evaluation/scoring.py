"""Cevapların kural tabanlı (LLM'siz) otomatik puanlanması.

Bu kontroller kaba ölçütlerdir: anahtar kelime eşleşmesi "doğru"nun yaklaşığıdır,
anlamı tam ölçmez. Daha ince değerlendirme için Faz 2.4 (groundedness) ve 2.8
(golden set) eklenecek.
"""

import re
from pathlib import Path

import yaml
from pydantic import BaseModel

# Cevabı dokümanda olan kategoriler (diğerleri: yok, sohbet, alakasiz)
ANSWERABLE = {"dogrudan", "cikarim"}
# Köşeli parantez içindeki atıfları yakalar: "[1]", "[K1]", "[12]"...
# [^\[\]]{1,10}: içinde köşeli parantez olmayan 1–10 karakter → geçersiz atıfları da yakalayabilmek için
# sadece rakam aramıyoruz. Parantez içi () grubu findall'un sadece içeriği ("1", "K1") döndürmesini sağlar.
CITATION = re.compile(r"\[([^\[\]]{1,10})\]")


# --- Veri modelleri (data/eval/questions.yaml'ın yapısı) ---
class EvalQuestion(BaseModel):
    id: str
    category: str
    question: str
    expected: str  # İnsan için beklenen cevap (raporda gösterilir, puanlamada kullanılmaz)
    must_contain: list[str] = []  # Cevapta geçmesi gereken ifadeler ("a|b" = a veya b)
    expected_chunk: int | None = None  # Cevabın bulunduğu chunk


class EvalSet(BaseModel):
    refusal_markers: list[str]  # "Bilgi yok / cevaplayamam" anlamına gelen ifadeler
    questions: list[EvalQuestion]


class Score(BaseModel):
    """Tek bir cevabın puanlama sonucu."""

    passed: bool
    content_ok: bool | None  # must_contain sağlandı mı (yalnızca cevaplanabilir sorular)
    refused: bool  # Cevapta ret ifadesi var mı
    citations: list[str]  # Cevaptaki tüm atıflar, örn. ["1", "K1"]
    invalid_citations: list[str]  # Bunlardan geçersiz olanlar, örn. ["K1"]
    cited_expected_chunk: bool | None  # doğru chunk'a atıf yapıldı mı (chunk getirildiyse)
    retrieval_rank: int | None  # beklenen chunk'ın retrieval sırası (1'den), yoksa None
    reason: str  # Başarısızsa kısa sebep ("atıf yok", "ret etmedi"...), başarılıysa ""


def load_eval_set(path: str | Path) -> EvalSet:
    """Soru setini YAML'dan okur; model_validate alanları ve tipleri doğrular."""
    return EvalSet.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def normalize(text: str) -> str:
    """Büyük/küçük harf duyarsız karşılaştırma için metni küçük harfe çevirir."""
    # Python'un lower()'ı Türkçeyi bilmez: "İ".lower() → "i̇" (i + birleşik nokta),
    # "I".lower() → "i" (Türkçede "ı" olmalı). Önce bu iki harfi elle düzeltiyoruz.
    return text.replace("İ", "i").replace("I", "ı").lower()


def contains_all(answer: str, requirements: list[str]) -> bool:
    """Her gereksinimden en az bir alternatif ("a|b") cevapta geçmeli."""
    text = normalize(answer)
    # Örn. requirements = ["hayır|ayrılamaz", "1 yıl|bir yıl"]:
    #   all(...) → her gereksinim sağlanmalı (VE)
    #   any(...) → gereksinimin "|" ile ayrılmış alternatiflerinden biri yeterli (VEYA)
    return all(any(normalize(alt) in text for alt in req.split("|")) for req in requirements)


def score_answer(
    question: EvalQuestion,
    answer: str,
    retrieved_chunks: list[int],  # Retrieval sırasıyla chunk_id'ler: [1]=retrieved_chunks[0], ...
    refusal_markers: list[str],
) -> Score:
    """Bir cevabı soru kategorisinin beklenen davranışına göre puanlar."""
    # --- Atıf analizi ---
    citations = CITATION.findall(answer)
    # 4 chunk getirildiyse geçerli atıflar "1".."4"
    valid_refs = {str(i) for i in range(1, len(retrieved_chunks) + 1)}
    invalid = [c for c in citations if c not in valid_refs]
    # Atıf numaralarını gerçek chunk_id'lere çevir: "[2]" → retrieved_chunks[1]
    cited_chunks = {retrieved_chunks[int(c) - 1] for c in citations if c in valid_refs}
    refused = any(normalize(m) in normalize(answer) for m in refusal_markers)

    # --- Retrieval analizi: beklenen chunk getirildi mi, kaçıncı sırada, ona atıf yapıldı mı ---
    rank = None
    cited_expected = None
    if question.expected_chunk is not None and question.expected_chunk in retrieved_chunks:
        rank = retrieved_chunks.index(question.expected_chunk) + 1
        cited_expected = question.expected_chunk in cited_chunks

    # --- Kategoriye göre geçti/kaldı kararı ---
    content_ok = None
    if question.category in ANSWERABLE:
        # Şirket sorusu: doğru bilgi + en az bir atıf + geçersiz atıf yok.
        # (Yanlış chunk'a atıf "kaldı" sayılmaz, sadece cited_expected_chunk'ta raporlanır.)
        content_ok = contains_all(answer, question.must_contain)
        if not content_ok:
            reason = "beklenen bilgi yok"
        elif invalid:
            reason = f"geçersiz atıf {invalid}"
        elif not citations:
            reason = "atıf yok"
        else:
            reason = ""
        passed = reason == ""
    elif question.category in {"yok", "alakasiz"}:
        # Dokümanda olmayan veya konu dışı: ret etmeli ve olmayan bir kaynağa atıf yapmamalı
        reason = "" if refused else "ret etmedi"
        if refused and citations:
            reason = "ret ama atıf var"
        passed = reason == ""
    elif question.category == "sohbet":
        # Selamlaşma: doğal karşılık vermeli; ne atıf ne de ret beklenir
        reason = "gereksiz atıf" if citations else ("ret etti" if refused else "")
        passed = reason == ""
    else:
        raise ValueError(f"Bilinmeyen kategori: {question.category}")

    return Score(
        passed=passed,
        content_ok=content_ok,
        refused=refused,
        citations=citations,
        invalid_citations=invalid,
        cited_expected_chunk=cited_expected,
        retrieval_rank=rank,
        reason=reason,
    )
