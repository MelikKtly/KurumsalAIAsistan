"""Tüm testler için ortak pytest ayarları (pytest bu dosyayı otomatik yükler)."""

import pytest

from app.config import get_settings


# autouse=True: bu fixture her testte, testin istemesine gerek kalmadan otomatik çalışır.
@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    """Testleri geliştiricinin .env ayarlarından bağımsız kılar.

    - İstek logu her testte geçici bir dosyaya yazılır (gerçek logs/ kirlenmez).
    - Groundedness hakemi varsayılan olarak kapalı: testlerin çoğu sahte bir sohbet
      modeli kullanır ve o model hakem olarak (yapılandırılmış çıktı) çalışamaz.
      Hakemi test eden testler onu `check_grounding=True` ile açıkça açar.
    """
    # Ortam değişkeni .env dosyasından önceliklidir (bkz. app/config.py)
    monkeypatch.setenv("GROUNDEDNESS_CHECK", "false")
    # İstek logu gerçek logs/ klasörüne değil, teste özel geçici bir dosyaya yazılsın
    monkeypatch.setenv("REQUEST_LOG_PATH", str(tmp_path / "requests.jsonl"))
    monkeypatch.setenv("AGENT_LOG_PATH", str(tmp_path / "agent.jsonl"))
    # get_settings lru_cache'li: önceki bir okumadan kalan nesneyi temizle ki yeni değer okunsun
    get_settings.cache_clear()
    yield
    # Test bitti: monkeypatch ortam değişkenini geri alır; cache'i de temizle ki
    # sonraki kod (veya test) gerçek ayarları okusun
    get_settings.cache_clear()
