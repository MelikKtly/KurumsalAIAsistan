"""İstek logundan (logs/requests.jsonl) performans özeti çıkarır.

Her adım için medyan (p50) ve p95 süre, ortalama token kullanımı, cevap türü
dağılımı ve hata sayısını yazdırır.

Kullanım:
    uv run python -m scripts.log_stats
    uv run python -m scripts.log_stats --log logs/requests.jsonl --last 50   # son 50 istek
"""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from app.config import get_settings


def percentile(values: list[float], p: float) -> float:
    """values'un p. yüzdeliği (0-100). Örn. p95: isteklerin %95'i bu süreden kısa.

    Ortalama yerine yüzdelik kullanılır: birkaç çok yavaş istek ortalamayı bozar ama
    medyanı bozmaz; p95 ise "kötü durumda kullanıcı ne kadar bekliyor" sorusunu cevaplar.
    """
    ordered = sorted(values)
    # En yakın sıra yöntemi: listenin p%'lik konumundaki eleman
    index = min(len(ordered) - 1, max(0, round(p / 100 * len(ordered)) - 1))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", default=get_settings().request_log_path)
    parser.add_argument("--last", type=int, help="Sadece son N isteği dahil et")
    args = parser.parse_args()

    path = Path(args.log)
    if not path.is_file():
        raise SystemExit(f"Log dosyası yok: {path} (önce API'ye birkaç istek atın)")

    # Her satır bağımsız bir JSON nesnesi (JSONL)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.last:
        records = records[-args.last :]
    ok = [r for r in records if r["status"] == "ok"]
    errors = [r for r in records if r["status"] != "ok"]

    print(f"Toplam istek: {len(records)}  (başarılı {len(ok)}, hata {len(errors)})")
    if not ok:
        return
    print(f"Zaman aralığı: {records[0]['timestamp'][:19]} → {records[-1]['timestamp'][:19]} (UTC)\n")

    # --- Süreler: her adım için p50/p95 ---
    print(f"{'Adım':<12} {'n':>4} {'p50 (ms)':>10} {'p95 (ms)':>10}")
    for step in ["retrieval_ms", "generation_ms", "grounding_ms", "total_ms"]:
        # grounding_ms hakem çalışmayan isteklerde None → onları dışarıda bırak
        values = [r["metrics"][step] for r in ok if r["metrics"][step] is not None]
        if values:
            name = step.removesuffix("_ms")
            print(f"{name:<12} {len(values):>4} {percentile(values, 50):>10.0f} {percentile(values, 95):>10.0f}")

    # --- Token kullanımı: istek başına ortalama ---
    print(f"\n{'Token (ort./istek)':<20} {'girdi':>8} {'çıktı':>8} {'toplam':>8}")
    for key, label in [("generation_tokens", "cevap üretimi"), ("grounding_tokens", "hakem"), ("total_tokens", "toplam")]:
        usages = [r["metrics"][key] for r in ok if r["metrics"][key] is not None]
        if usages:
            avg = {k: statistics.mean(u[k] for u in usages) for k in ("input_tokens", "output_tokens", "total_tokens")}
            print(f"{label:<20} {avg['input_tokens']:>8.0f} {avg['output_tokens']:>8.0f} {avg['total_tokens']:>8.0f}")

    # --- Cevap türleri ve hakem sonuçları ---
    print("\nCevap türleri:", dict(Counter(r["answer_type"] for r in ok)))
    grounded = Counter(r["grounded"] for r in ok if r["grounded"] is not None)
    if grounded:
        print(f"Hakem: {grounded.get(True, 0)} doğrulandı, {grounded.get(False, 0)} uydurma şüphesi")


if __name__ == "__main__":
    main()
