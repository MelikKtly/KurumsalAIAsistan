"""Token kullanımından maliyet (USD) hesabı.

İki maliyet hesaplanır:
  - usd:           isteği gerçekten işleyen modelin maliyeti (Ollama lokal → 0)
  - reference_usd: aynı istek referans bir API modeliyle (.env: COST_REFERENCE_MODEL)
                   yapılsaydı yaklaşık ne tutardı — "API'ye geçersek ne öderiz?" sorusu için
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.observability import CostEstimate, TokenUsage

PRICING_FILE = Path(__file__).parent / "pricing.yaml"
MTOK = 1_000_000  # Fiyatlar "1 milyon token başına" verildiği için bölen


class ModelPrice(BaseModel):
    input_per_mtok: float
    output_per_mtok: float


# Fiyat dosyası her istekte tekrar okunmasın
@lru_cache
def load_prices() -> dict[str, ModelPrice]:
    data = yaml.safe_load(PRICING_FILE.read_text(encoding="utf-8"))
    return {name: ModelPrice(**price) for name, price in data["models"].items()}


def cost_usd(usage: TokenUsage, model: str) -> float | None:
    """Kullanımın verilen modeldeki maliyeti. Model tabloda yoksa None (0 demek yanıltıcı olurdu)."""
    price = load_prices().get(model)
    if price is None:
        return None
    # Girdi ve çıktı token'ları farklı fiyatlanır (çıktı genelde 5 kat pahalı)
    usd = usage.input_tokens / MTOK * price.input_per_mtok + usage.output_tokens / MTOK * price.output_per_mtok
    # Tek bir istek çok ucuz olduğundan (örn. $0.0048) 8 ondalık basamak tutulur
    return round(usd, 8)


def estimate_cost(usage: TokenUsage, model: str, reference_model: str) -> CostEstimate:
    return CostEstimate(
        model=model,
        usd=cost_usd(usage, model),
        reference_model=reference_model,
        reference_usd=cost_usd(usage, reference_model),
    )
