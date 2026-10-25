"""Cevapların kural tabanlı (LLM'siz) otomatik puanlanması.

Bu kontroller kaba ölçütlerdir: anahtar kelime eşleşmesi "doğru"nun yaklaşığıdır,
anlamı tam ölçmez. Daha ince değerlendirme için Faz 2.4 (groundedness) ve 2.8
(golden set) eklenecek.
"""

import re
from pathlib import Path

import yaml
from pydantic import BaseModel

ANSWERABLE = {"dogrudan", "cikarim"}
CITATION = re.compile(r"\[([^\[\]]{1,10})\]")


class EvalQuestion(BaseModel):
    id: str
    category: str
    question: str
    expected: str
    must_contain: list[str] = []
    expected_chunk: int | None = None


class EvalSet(BaseModel):
    refusal_markers: list[str]
    questions: list[EvalQuestion]


class Score(BaseModel):
    passed: bool
    content_ok: bool | None  # must_contain sağlandı mı (yalnızca cevaplanabilir sorular)
    refused: bool
    citations: list[str]
    invalid_citations: list[str]
    cited_expected_chunk: bool | None  # doğru chunk'a atıf yapıldı mı (chunk getirildiyse)
    retrieval_rank: int | None  # beklenen chunk'ın retrieval sırası (1'den), yoksa None
    reason: str


def load_eval_set(path: str | Path) -> EvalSet:
    return EvalSet.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def normalize(text: str) -> str:
    # Türkçe "İ".lower() → "i̇" (birleşik nokta) sorununu gider
    return text.replace("İ", "i").replace("I", "ı").lower()


def contains_all(answer: str, requirements: list[str]) -> bool:
    """Her gereksinimden en az bir alternatif ("a|b") cevapta geçmeli."""
    text = normalize(answer)
    return all(any(normalize(alt) in text for alt in req.split("|")) for req in requirements)


def score_answer(
    question: EvalQuestion,
    answer: str,
    retrieved_chunks: list[int],
    refusal_markers: list[str],
) -> Score:
    citations = CITATION.findall(answer)
    valid_refs = {str(i) for i in range(1, len(retrieved_chunks) + 1)}
    invalid = [c for c in citations if c not in valid_refs]
    cited_chunks = {retrieved_chunks[int(c) - 1] for c in citations if c in valid_refs}
    refused = any(normalize(m) in normalize(answer) for m in refusal_markers)

    rank = None
    cited_expected = None
    if question.expected_chunk is not None and question.expected_chunk in retrieved_chunks:
        rank = retrieved_chunks.index(question.expected_chunk) + 1
        cited_expected = question.expected_chunk in cited_chunks

    content_ok = None
    if question.category in ANSWERABLE:
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
        reason = "" if refused else "ret etmedi"
        if refused and citations:
            reason = "ret ama atıf var"
        passed = reason == ""
    elif question.category == "sohbet":
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
