"""Text-to-SQL aracı — Faz 4.3.

Agent, çalışanlara özgü bilgi (kıdem, kullanılan izin, şehir...) gerektiğinde bu araca
kendi yazdığı SQL'i verir. Böylece aynı sistemde iki farklı veri kaynağı birlikte kullanılır:
  - search_documents → Chroma (vektör DB): şirket KURALLARI (örn. "5–15 yıl kıdem = 20 gün izin")
  - query_employees  → Postgres/SQLite: çalışan VERİSİ (örn. "Ayşe 2019'da başladı")

GÜVENLİK: SQL'i LLM yazıyor, yani güvenilmez girdi. Katmanlı koruma:
  1. Yalnızca tek bir SELECT (veya WITH ... SELECT) ifadesi; yazma/şema komutları reddedilir
  2. Yalnızca izinli tablolar (employees) — query_logs gibi kullanıcı verisi içeren tablolar kapalı
  3. Veritabanı seviyesinde SALT-OKUNUR çalıştırma (1–2 aşılsa bile veri değiştirilemez)
  4. En fazla MAX_ROWS satır döner
"""

import re
from datetime import date

from langchain_core.tools import tool
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_engine

ALLOWED_TABLES = {"employees"}
MAX_ROWS = 50
# Kelime sınırıyla (\b) aranır: "created_at" gibi sütun adları "create" sayılmasın
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|attach|detach|pragma|copy|vacuum|replace)\b",
    re.IGNORECASE,
)
# FROM / JOIN'den sonra gelen tablo adları
TABLE_REF = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_\.\"]*)", re.IGNORECASE)
# WITH ile tanımlanan geçici ad (CTE): "WITH t AS (" veya ", t AS (" — bunlar gerçek tablo değil
CTE_NAME = re.compile(r"(?:\bwith|,)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(", re.IGNORECASE)


def validate_sql(sql: str) -> str | None:
    """SQL güvenliyse None, değilse reddetme sebebini döner."""
    stripped = sql.strip().rstrip(";").strip()
    if ";" in stripped:
        return "Yalnızca tek bir SQL ifadesine izin var."
    if not re.match(r"^(select|with)\b", stripped, re.IGNORECASE):
        return "Yalnızca SELECT sorgularına izin var."
    if match := FORBIDDEN.search(stripped):
        return f"İzin verilmeyen komut: {match.group(1).upper()}"
    ctes = {c.lower() for c in CTE_NAME.findall(stripped)}
    tables = {t.strip('"').split(".")[-1].lower() for t in TABLE_REF.findall(stripped)} - ctes
    if not tables:
        return "Sorguda tablo bulunamadı."
    if disallowed := tables - ALLOWED_TABLES:
        return f"Bu tablolara erişim yok: {sorted(disallowed)}. İzinli: {sorted(ALLOWED_TABLES)}"
    return None


def run_readonly_query(sql: str, engine: Engine | None = None) -> str:
    """Doğrulanmış SQL'i salt-okunur bağlantıda çalıştırır ve sonucu metin tablo olarak döner."""
    if error := validate_sql(sql):
        return f"HATA: Sorgu reddedildi — {error}"
    engine = engine or get_engine()
    is_sqlite = engine.dialect.name == "sqlite"
    try:
        with engine.connect() as conn:
            # Veritabanı seviyesinde salt-okunur: doğrulama bir şekilde aşılsa bile yazma başarısız olur
            if is_sqlite:
                conn.exec_driver_sql("PRAGMA query_only = ON")
            else:
                conn.exec_driver_sql("SET TRANSACTION READ ONLY")
            try:
                result = conn.execute(text(sql.strip().rstrip(";")))
                columns = list(result.keys())
                rows = result.fetchmany(MAX_ROWS + 1)  # +1: sınırın aşılıp aşılmadığını anlamak için
            finally:
                if is_sqlite:
                    # Bağlantı havuza geri döneceği için ayarı eski haline getir
                    conn.exec_driver_sql("PRAGMA query_only = OFF")
                conn.rollback()  # Salt-okunur işlemi kapat
    except SQLAlchemyError as exc:
        # Model hatalı SQL yazarsa (yanlış sütun adı vb.) hatayı ona geri ver; düzeltip tekrar deneyebilir
        return f"HATA: SQL çalıştırılamadı — {str(exc.orig if hasattr(exc, 'orig') else exc)[:300]}"

    if not rows:
        return "Sorgu sonuç döndürmedi (0 satır)."
    truncated = len(rows) > MAX_ROWS
    lines = [" | ".join(columns)] + [" | ".join(str(v) for v in row) for row in rows[:MAX_ROWS]]
    if truncated:
        lines.append(f"(İlk {MAX_ROWS} satır gösteriliyor)")
    return "\n".join(lines)


@tool
def query_employees(sql: str) -> str:
    """Çalışan veritabanında salt-okunur bir SQL SELECT sorgusu çalıştırır.
    Belirli bir çalışanın bilgisi (işe başlama tarihi/kıdem, bu yıl kullandığı izin, şehir,
    departman, uzaktan çalışma günü) gerektiğinde kullan. Şirket KURALLARI için search_documents kullan.

    Tablo: employees
      id (int), full_name (metin, örn. 'Ayşe Yılmaz'), department (metin), city (metin: İstanbul/Ankara/İzmir),
      start_date (tarih, işe başlama), used_leave_days (int, bu yıl kullanılan yıllık izin günü),
      remote_days_per_week (int, haftalık uzaktan çalışma günü)

    Kurallar: Yalnızca SELECT. İsimleri LIKE ile ara (örn. full_name LIKE '%Ayşe%').
    Tarih hesabını SQL'de yapma: start_date'i çek, kıdemi bugünün tarihine göre kendin hesapla."""
    result = run_readonly_query(sql)
    # Kıdem hesabı için bugünün tarihi: model kendi "bugün" bilgisine güvenmesin
    return f"Bugünün tarihi: {date.today().isoformat()}\n{result}"
