"""Yapılandırılmış (JSON) loglama — Faz 4.4.

Her log satırı tek bir JSON nesnesidir:
    {"ts": "2026-10-27T16:05:01.123+00:00", "level": "INFO", "logger": "app.api",
     "msg": "request_finished", "endpoint": "/ask", "status": 200, "duration_ms": 8123.4, "request_id": "a1b2..."}

Neden JSON: Loglar insan için değil makine için de okunabilir olur; Loki/Elasticsearch/Datadog
gibi araçlar alanlara göre filtreleyip (örn. level=ERROR, endpoint=/agent) grafik çizebilir.

Seviyeler (LOG_LEVEL ile seçilir, varsayılan INFO):
    DEBUG   → ayrıntı (agent'ın her adımı, her araç çağrısı)
    INFO    → normal olaylar (istek başladı/bitti)
    WARNING → beklenmedik ama sistem çalışmaya devam ediyor (araç hatası, adım limiti doldu)
    ERROR   → istek başarısız (Ollama'ya ulaşılamadı)

Kullanım:
    logger = logging.getLogger(__name__)
    logger.info("request_finished", extra={"endpoint": "/ask", "duration_ms": 812.3})
`extra` içindeki alanlar JSON satırına ayrı anahtarlar olarak eklenir.
"""

import json
import logging
from datetime import datetime, timezone

# logging.LogRecord'un kendi standart alanları — bunlar dışındaki her şey `extra` ile eklenmiştir
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


class JSONFormatter(logging.Formatter):
    """LogRecord'u tek satırlık JSON'a çevirir."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # extra={...} ile verilen alanlar (endpoint, duration_ms, tool...)
        payload.update({k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # default=str: JSON'a doğrudan çevrilemeyen değerler (datetime vb.) metne çevrilir
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Uygulamanın ("app.*") loglarını JSON formatında standart çıktıya (stdout) yönlendirir.

    stdout: Docker/Kubernetes'te konteyner logları stdout'tan toplanır (12-factor app ilkesi).
    Tekrar çağrılması güvenlidir (handler iki kez eklenmez).
    """
    logger = logging.getLogger("app")
    logger.setLevel(level.upper())
    if not any(getattr(h, "_kurumsal_json", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        handler._kurumsal_json = True  # Bizim handler'ımız olduğunu işaretle
        logger.addHandler(handler)
    # Kök logger'a da iletilmesin (uvicorn'un kendi formatında ikinci kez basılmasın)
    logger.propagate = False
