"""Groundedness hakeminin ne kadar güvenilir olduğunu ölçer.

data/eval/groundedness.yaml'daki sabit cevapları (bağlama dayalı ve uydurma)
hakeme verir ve kararlarını beklenenle karşılaştırır. Sonuç Markdown rapor
olarak yazılır.

Kullanım:
    uv run python -m scripts.eval_groundedness
    uv run python -m scripts.eval_groundedness --out docs/groundedness_degerlendirme.md
"""

import argparse
import time
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.config import get_settings
from app.retrieval.groundedness import check_groundedness, get_groundedness_prompt
from app.retrieval.retriever import retrieve


class Case(BaseModel):
    id: str
    question: str
    answer: str
    expected_grounded: bool
    note: str = ""


def cell(text: str, limit: int = 120) -> str:
    """Metni Markdown tablo hücresine uygun hale getirir (tek satır, | kaçışlı, kısaltılmış)."""
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", default="data/eval/groundedness.yaml")
    parser.add_argument("--out", default="docs/groundedness_degerlendirme.md")
    args = parser.parse_args()

    raw = yaml.safe_load(Path(args.cases).read_text(encoding="utf-8"))
    cases = [Case.model_validate(c) for c in raw["cases"]]

    results = []
    for case in cases:
        # Bağlam, gerçek sistemde olduğu gibi retrieval ile getirilir
        documents = retrieve(case.question)
        start = time.perf_counter()
        verdict = check_groundedness(case.question, case.answer, documents)
        seconds = time.perf_counter() - start
        # verdict None ise hakem geçerli bir karar üretemedi → hata sayılır
        got = None if verdict is None else verdict.grounded
        correct = got == case.expected_grounded
        results.append((case, verdict, got, correct, seconds))
        print(f"[{seconds:4.1f} sn] {case.id} beklenen={case.expected_grounded!s:5} hakem={got!s:5} {'✅' if correct else '❌'}")

    # --- Metrikler ---
    # Bu bağlamda "pozitif" = uydurma (grounded=False); hakemin asıl görevi uydurmayı yakalamak.
    ungrounded = [r for r in results if not r[0].expected_grounded]
    grounded = [r for r in results if r[0].expected_grounded]
    caught = sum(r[2] is False for r in ungrounded)  # Uydurmayı doğru yakaladı
    false_alarm = sum(r[2] is False for r in grounded)  # Doğru cevaba "uydurma" dedi
    invalid = sum(r[2] is None for r in results)  # Geçerli karar üretemedi
    accuracy = sum(r[3] for r in results)
    times = [r[4] for r in results]
    avg = sum(times[1:]) / max(len(times) - 1, 1)  # İlk çağrı model ısınması, hariç

    lines = [
        "# Groundedness Hakemi Değerlendirmesi",
        "",
        f"**Tarih:** {date.today().isoformat()}  ",
        f"**Hakem modeli:** `{get_settings().llm_model}` · **Prompt:** `groundedness/{get_groundedness_prompt().version}`  ",
        f"**Vaka seti:** `{args.cases}` ({len(cases)} vaka: {len(grounded)} bağlama dayalı, {len(ungrounded)} uydurma)  ",
        f"**Yeniden üretmek için:** `uv run python -m scripts.eval_groundedness --out {args.out}`",
        "",
        "## Özet",
        "",
        "| Ölçüt | Sonuç |",
        "| --- | --- |",
        f"| **Doğruluk** | **{accuracy}/{len(results)}** |",
        f"| Uydurmayı yakalama (recall) | {caught}/{len(ungrounded)} |",
        f"| Yanlış alarm (doğru cevaba \"uydurma\") | {false_alarm}/{len(grounded)} |",
        f"| Geçersiz karar (şemaya uymayan çıktı) | {invalid} |",
        f"| Ortalama hakem süresi (ilk hariç) | {avg:.1f} sn |",
        "",
        "## Vaka bazında",
        "",
        "| id | Not | Cevap | Beklenen | Hakem | Hakemin desteksiz bulduğu / gerekçe |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case, verdict, got, correct, _ in results:
        mark = "✅" if correct else "❌"
        detail = "—" if verdict is None else "; ".join(verdict.unsupported_claims) or verdict.claims_check
        expected = "dayanıyor" if case.expected_grounded else "uydurma"
        judged = "geçersiz" if got is None else ("dayanıyor" if got else "uydurma")
        lines.append(
            f"| {case.id} | {cell(case.note, 50)} | {cell(case.answer, 90)} | {expected} | {mark} {judged} | {cell(detail, 100)} |"
        )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nDoğruluk {accuracy}/{len(results)} · yakalama {caught}/{len(ungrounded)} · yanlış alarm {false_alarm}/{len(grounded)}")
    print(f"Rapor: {args.out}")


if __name__ == "__main__":
    main()
