"""Golden set'i sistemin üretimdeki ayarlarıyla (aktif prompt, hakem vb.) çalıştırır.

Her soru için tam RAG akışı (answer_question) çalışır; cevap, cevap türü, hakem
kararı, süre ve token kaydedilir. Otomatik kontroller (must_contain, answer_type)
yapılır; elle değerlendirme için sonuçlar JSON olarak yazılır.

Kullanım:
    uv run python -m scripts.run_golden --out logs/golden_sonuclar.json
    uv run python -m scripts.run_golden --min-pass 13   # 13/15'in altında kalırsa hata koduyla çık

--min-pass ile "kalite kapısı" olarak kullanılabilir: bir değişiklikten (prompt, model, chunk ayarı)
sonra çalıştırılır; başarı eşiğin altına düşerse çıkış kodu 1 olur (CI'da adımı başarısız sayar).
"""

import argparse
import json
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.config import get_settings
from app.evaluation.scoring import contains_all
from app.retrieval.rag import answer_question


class GoldenQuestion(BaseModel):
    id: str
    question: str
    reference_answer: str
    must_contain: list[str] = []
    expected_answer_type: str


def load_golden(path: str | Path) -> list[GoldenQuestion]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [GoldenQuestion.model_validate(q) for q in data["questions"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--golden", default="data/eval/golden_set.yaml")
    parser.add_argument("--out", default="logs/golden_sonuclar.json")
    parser.add_argument("--min-pass", type=int, help="Otomatik kontrolden geçmesi gereken en az soru sayısı")
    args = parser.parse_args()

    settings = get_settings()
    results = []
    for q in load_golden(args.golden):
        r = answer_question(q.question)
        # Otomatik kontroller: doğru cevap türü mü, beklenen bilgi geçiyor mu?
        type_ok = r.answer_type == q.expected_answer_type
        content_ok = contains_all(r.answer, q.must_contain) if q.must_contain else None
        auto_pass = type_ok and content_ok is not False
        results.append(
            {
                "id": q.id,
                "question": q.question,
                "reference_answer": q.reference_answer,
                "answer": r.answer,
                "answer_type": r.answer_type,
                "expected_answer_type": q.expected_answer_type,
                "type_ok": type_ok,
                "content_ok": content_ok,
                "auto_pass": auto_pass,
                "grounded": r.groundedness.grounded if r.groundedness else None,
                "unsupported_claims": r.groundedness.unsupported_claims if r.groundedness else [],
                "cited_pages": [s.page for s in r.sources if s.cited],
                "total_ms": r.metrics.total_ms,
                "total_tokens": r.metrics.total_tokens.total_tokens,
            }
        )
        mark = "✅" if auto_pass else "❌"
        print(f"{mark} {q.id} [{r.answer_type}] {r.metrics.total_ms / 1000:4.1f} sn | {' '.join(r.answer.split())[:90]}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps({"llm_model": settings.llm_model, "prompt_version": settings.rag_prompt_version,
                    "groundedness_check": settings.groundedness_check, "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    passed = sum(r["auto_pass"] for r in results)
    print(f"\nOtomatik kontrol: {passed}/{len(results)} · Sonuçlar: {args.out}")
    if args.min_pass is not None and passed < args.min_pass:
        print(f"BAŞARISIZ: {passed} < eşik {args.min_pass}")
        sys.exit(1)  # Çıkış kodu 1 → kalite kapısı geçilemedi


if __name__ == "__main__":
    main()
