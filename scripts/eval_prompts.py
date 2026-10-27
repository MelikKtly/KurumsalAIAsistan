"""Prompt versiyonlarını aynı soru setinde karşılaştırır ve Markdown rapor yazar.

Her soru için retrieval bir kez yapılır; aynı chunk'lar her versiyona verilir,
böylece fark yalnızca prompttan gelir. Puanlama kural tabanlıdır
(app/evaluation/scoring.py).

Kullanım:
    uv run python -m scripts.eval_prompts                          # tüm versiyonlar
    uv run python -m scripts.eval_prompts --versions v1 v2 --out docs/prompt_karsilastirma.md
"""

import argparse
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.evaluation.scoring import ANSWERABLE, Score, load_eval_set, score_answer
from app.prompts.loader import available_versions, load_prompt
from app.retrieval.rag import generate_answer
from app.retrieval.retriever import retrieve

# Rapor tablolarında kategori kodlarının (YAML'daki) okunur adları
CATEGORY_NAMES = {
    "dogrudan": "Doğrudan bilgi",
    "cikarim": "Çıkarım",
    "yok": "Dokümanda yok",
    "sohbet": "Selamlaşma",
    "alakasiz": "Konu dışı",
}


def run(versions: list[str], questions_path: str) -> tuple[list[dict], dict]:
    """Her soruyu her prompt versiyonuyla çalıştırıp puanlar.

    Dönüş: (satırlar, meta). Her satır = bir soru + her versiyonun cevabı/süresi/puanı.
    """
    eval_set = load_eval_set(questions_path)
    # Promptlar döngüden önce bir kez yüklenir (ve dosya hataları en başta yakalanır)
    prompts = {v: load_prompt("rag", v) for v in versions}
    rows = []
    for q in eval_set.questions:
        # Retrieval soru başına BİR kez: aynı chunk'lar tüm versiyonlara verilir,
        # böylece sonuç farkı yalnızca prompttan kaynaklanır (adil karşılaştırma).
        documents = retrieve(q.question)
        chunks = [d.metadata["chunk_id"] for d in documents]
        row = {"q": q, "chunks": chunks, "results": {}}
        for v, prompt in prompts.items():
            start = time.perf_counter()  # Süre sadece LLM üretimini ölçer (retrieval hariç)
            answer = generate_answer(q.question, documents, prompt=prompt).text
            seconds = time.perf_counter() - start
            score = score_answer(q, answer, chunks, eval_set.refusal_markers, eval_set.off_topic_markers)
            row["results"][v] = {"answer": answer, "seconds": seconds, "score": score}
            mark = "✅" if score.passed else f"❌ {score.reason}"
            # Uzun süren çalıştırmada ilerlemeyi canlı görmek için her sonucu yazdır
            print(f"[{v} {seconds:4.1f} sn] {q.id} {q.question[:50]:50} {mark}")
        rows.append(row)
    # Raporun başına yazılacak bilgiler: sonuç hangi model/ayarlarla üretildi (tekrar üretilebilirlik)
    meta = {
        "llm": get_settings().llm_model,
        "embedding": get_settings().embedding_model,
        "top_k": get_settings().top_k,
        "questions": questions_path,
        "descriptions": {v: p.description for v, p in prompts.items()},
    }
    return rows, meta


def pct(n: int, d: int) -> str:
    """Oranı "8/9 (%89)" biçiminde yazar; payda 0 ise "—"."""
    return f"{n}/{d} (%{round(100 * n / d)})" if d else "—"


def cell(text: str, limit: int = 140) -> str:
    """Metni Markdown tablo hücresine uygun hale getirir."""
    # Satır sonları tabloyu bozar → tek satıra indir; "|" sütun ayracıdır → kaçış karakteriyle yaz
    text = " ".join(text.split()).replace("|", "\\|")
    # Çok uzun cevapları kısalt ki tablo okunabilir kalsın
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize(rows: list[dict], version: str) -> dict:
    """Bir versiyonun tüm sorulardaki sonuçlarını özet metriklere indirger."""
    # Her soru için (kategori, puan, süre) üçlüsü
    scores: list[tuple[str, Score, float]] = [
        (r["q"].category, r["results"][version]["score"], r["results"][version]["seconds"]) for r in rows
    ]
    # Kategori başına [geçen, toplam]; defaultdict sayesinde ilk görülen kategori otomatik [0, 0] başlar
    by_cat = defaultdict(lambda: [0, 0])
    for cat, s, _ in scores:
        by_cat[cat][0] += s.passed  # bool toplanabilir: True=1, False=0
        by_cat[cat][1] += 1
    answerable = [s for c, s, _ in scores if c in ANSWERABLE]
    # "Doğru chunk'a atıf" sadece doğru chunk getirildiyse ölçülebilir (getirilmediyse None)
    with_chunk = [s for s in answerable if s.cited_expected_chunk is not None]
    times = [t for _, _, t in scores]
    return {
        "passed": pct(sum(s.passed for _, s, _ in scores), len(scores)),
        "by_cat": {c: pct(*by_cat[c]) for c in CATEGORY_NAMES if c in by_cat},
        "content": pct(sum(bool(s.content_ok) for s in answerable), len(answerable)),
        "cited_expected": pct(sum(s.cited_expected_chunk for s in with_chunk), len(with_chunk)),
        "invalid_citations": sum(len(s.invalid_citations) for _, s, _ in scores),
        "avg_seconds": f"{sum(times[1:]) / max(len(times) - 1, 1):.1f} sn",  # ilk çağrı ısınma, hariç
    }


def write_report(rows: list[dict], meta: dict, versions: list[str], out: Path) -> None:
    """Sonuçları Markdown rapor olarak yazar: başlık bilgileri, özet tablo, soru bazında tablo."""
    summaries = {v: summarize(rows, v) for v in versions}
    # Tablo başlığı versiyon sayısına göre dinamik: "| Ölçüt | v1 | v2 |" + ayraç satırı
    header = "| Ölçüt | " + " | ".join(versions) + " |\n| --- |" + " --- |" * len(versions)
    lines = [
        "# Prompt Versiyonları Karşılaştırması",
        "",
        f"**Tarih:** {date.today().isoformat()}  ",
        f"**LLM:** `{meta['llm']}` · **Embedding:** `{meta['embedding']}` · **top_k:** {meta['top_k']}  ",
        f"**Soru seti:** `{meta['questions']}` ({len(rows)} soru)  ",
        "**Yeniden üretmek için:** `uv run python -m scripts.eval_prompts --versions "
        + " ".join(versions)
        + f" --out {out}`",
        "",
        "Her soru için retrieval bir kez yapıldı; aynı chunk'lar her versiyona verildi.",
        "Puanlama kural tabanlıdır (anahtar kelime, ret ifadesi, atıf geçerliliği) — anlamı tam ölçmez.",
        "",
        "## Versiyonlar",
        "",
        *[f"- **{v}:** {meta['descriptions'][v]}" for v in versions],
        "",
        "## Özet",
        "",
        header,
        "| **Toplam geçen** | " + " | ".join(f"**{summaries[v]['passed']}**" for v in versions) + " |",
    ]
    for cat, name in CATEGORY_NAMES.items():
        if cat in summaries[versions[0]]["by_cat"]:
            lines.append(f"| {name} | " + " | ".join(summaries[v]["by_cat"][cat] for v in versions) + " |")
    lines += [
        "| Beklenen bilgi cevapta (cevaplanabilir) | " + " | ".join(summaries[v]["content"] for v in versions) + " |",
        "| Doğru chunk'a atıf (chunk getirildiyse) | " + " | ".join(summaries[v]["cited_expected"] for v in versions) + " |",
        "| Geçersiz atıf sayısı | " + " | ".join(str(summaries[v]["invalid_citations"]) for v in versions) + " |",
        "| Ortalama süre (ilk hariç) | " + " | ".join(summaries[v]["avg_seconds"] for v in versions) + " |",
        "",
        "## Soru bazında",
        "",
        "| id | Soru | Beklenen | Retrieval sırası | "
        + " | ".join(versions)
        + " |\n| --- | --- | --- | --- |"
        + " --- |" * len(versions),
    ]
    # Soru bazında tablo: her versiyon için ✅/❌ + sebep + kısaltılmış cevap
    for r in rows:
        q = r["q"]
        # Retrieval tüm versiyonlarda aynı olduğu için sıra ilk versiyonun puanından okunabilir
        rank = r["results"][versions[0]]["score"].retrieval_rank
        # "—": soru için beklenen chunk yok (yok/sohbet/alakasiz); "❌ yok": chunk ilk k'ya girmedi
        rank_txt = "—" if q.expected_chunk is None else (str(rank) if rank else "❌ yok")
        cells = []
        for v in versions:
            res = r["results"][v]
            s = res["score"]
            mark = "✅" if s.passed else f"❌ *{s.reason}*"
            cells.append(f"{mark}<br>{cell(res['answer'])}")  # <br>: hücre içinde satır atlama
        lines.append(f"| {q.id} | {cell(q.question, 60)} | {cell(q.expected, 40)} | {rank_txt} | " + " | ".join(cells) + " |")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nRapor: {out}")


def main() -> None:
    # Komut satırı argümanları; --help ile modül açıklaması (__doc__) gösterilir
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--versions", nargs="+", default=available_versions("rag"))
    parser.add_argument("--questions", default="data/eval/questions.yaml")
    parser.add_argument("--out", default="docs/prompt_karsilastirma.md")
    parser.add_argument("--json", help="Ham sonuçları JSON olarak da kaydet")
    args = parser.parse_args()

    rows, meta = run(args.versions, args.questions)
    write_report(rows, meta, args.versions, Path(args.out))
    # İstenirse ham sonuçlar (tam cevaplar, tüm puan alanları) JSON olarak da kaydedilir;
    # rapordaki kısaltılmış cevapların ötesinde detaylı inceleme için
    if args.json:
        raw = [
            {
                "id": r["q"].id,
                "question": r["q"].question,
                "chunks": r["chunks"],
                "results": {
                    v: {"answer": x["answer"], "seconds": round(x["seconds"], 2), **x["score"].model_dump()}
                    for v, x in r["results"].items()
                },
            }
            for r in rows
        ]
        Path(args.json).write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
