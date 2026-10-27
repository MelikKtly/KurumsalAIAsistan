"""Gözlemlenebilirlik: istek başına süre (latency) ve token ölçümü + JSONL istek logu.

Her /ask isteği için:
  - hangi adım ne kadar sürdü (retrieval, cevap üretimi, hakem, toplam)
  - her LLM çağrısı kaç girdi/çıktı token'ı kullandı
ölçülür; API cevabında `metrics` olarak döner ve logs/requests.jsonl'a bir satır yazılır.
Bu veriler Faz 2.6'daki maliyet hesabının ve Faz 4'teki Postgres kaydının temelidir.
"""

import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage
from pydantic import BaseModel, computed_field


class TokenUsage(BaseModel):
    """Bir veya birkaç LLM çağrısının token kullanımı."""

    input_tokens: int = 0  # Modele giden: prompt + bağlam + soru
    output_tokens: int = 0  # Modelin ürettiği

    # computed_field: saklanmaz, her seferinde hesaplanır; ama JSON çıktısına dahil edilir
    @computed_field
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @classmethod
    def from_message(cls, message: AIMessage | None) -> "TokenUsage":
        """LangChain mesajındaki usage_metadata'dan okur.

        Ollama (ve Claude/OpenAI) token sayılarını cevapla birlikte döndürür; LangChain bunları
        `message.usage_metadata = {"input_tokens": .., "output_tokens": .., ...}` olarak sunar.
        Sahte test modelleri bu bilgiyi vermez → None → sıfır.
        """
        usage = getattr(message, "usage_metadata", None) or {}
        return cls(input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0))

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        # İki kullanımı toplamak için: generation + grounding = toplam
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


class RequestMetrics(BaseModel):
    """Bir /ask isteğinin ölçümleri (süreler milisaniye)."""

    retrieval_ms: float
    generation_ms: float
    grounding_ms: float | None = None  # Hakem çalışmadıysa None
    total_ms: float
    generation_tokens: TokenUsage
    grounding_tokens: TokenUsage | None = None

    @computed_field
    @property
    def total_tokens(self) -> TokenUsage:
        """Tüm LLM çağrılarının toplam token kullanımı (cevap + hakem)."""
        return self.generation_tokens + (self.grounding_tokens or TokenUsage())


@contextmanager
def timer() -> Iterator[dict[str, float]]:
    """`with` bloğunun süresini ölçer.

    Kullanım:
        with timer() as t:
            ...iş...
        print(t["ms"])
    Blok bittiğinde (hata olsa bile — finally) t["ms"] doldurulur.
    """
    result: dict[str, float] = {}
    # perf_counter: süre ölçümü için monoton, yüksek çözünürlüklü saat
    # (time.time() sistem saati değişince geri gidebilir; süre ölçümüne uygun değildir)
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["ms"] = round((time.perf_counter() - start) * 1000, 1)


# Aynı anda gelen istekler (FastAPI senkron endpoint'leri thread havuzunda çalıştırır)
# aynı dosyaya yazarken satırların birbirine karışmaması için kilit.
_log_lock = threading.Lock()


def append_request_log(record: dict[str, Any], path: str | Path) -> None:
    """İstek kaydını JSONL dosyasına bir satır olarak ekler.

    JSONL (JSON Lines): her satır bağımsız bir JSON nesnesi. Dosyanın sonuna ekleme
    yapmak ucuzdur ve satır satır okunup analiz edilebilir (bkz. scripts/log_stats.py).
    (Faz 4'te bu kayıtlar Postgres'e, loglama da yapılandırılmış logging'e taşınacak.)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Zaman damgası UTC ve ISO formatında: farklı saat dilimlerinde karışıklık olmasın
    line = json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), **record}, ensure_ascii=False)
    with _log_lock, path.open("a", encoding="utf-8") as f:  # "a": dosyanın sonuna ekle
        f.write(line + "\n")
