"""İlişkisel veritabanı katmanı (SQLAlchemy) — Faz 4.2/4.3.

İki tablo:
  - query_logs: /ask ve /agent isteklerinin geçmişi (soru, cevap, araçlar, süre, token, maliyet)
  - employees:  text-to-SQL aracı için kurgusal çalışan verisi (Faz 4.3)

Bağlantı adresi .env'deki DATABASE_URL'den gelir:
  - Docker Compose'da PostgreSQL:  postgresql+psycopg://kullanici:sifre@postgres:5432/kurumsal
  - Lokal geliştirme / testler:    sqlite:///data/app.db  (kurulum gerektirmez)
SQLAlchemy ikisini de aynı kodla yönettiği için uygulama kodu değişmez.
"""

from collections.abc import Iterator
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings


# Tüm ORM modellerinin ortak tabanı. Bir sınıf bundan türeyince SQLAlchemy onu bir tabloya eşler.
class Base(DeclarativeBase):
    pass


class QueryLog(Base):
    """Bir /ask veya /agent isteğinin kaydı."""

    __tablename__ = "query_logs"

    # Mapped[tip] + mapped_column(...): Python tipi ile veritabanı sütununu birlikte tanımlar
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    endpoint: Mapped[str] = mapped_column(String(20))  # "ask" | "agent"
    status: Mapped[str] = mapped_column(String(20))  # "ok" | "error"
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # yalnızca /ask
    grounded: Mapped[bool | None] = mapped_column(nullable=True)  # hakem kararı (yalnızca /ask)
    llm_model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # JSON sütunu: Postgres'te JSON, SQLite'ta metin olarak saklanır; Python'da liste/sözlük olarak okunur
    tools_used: Mapped[list] = mapped_column(JSON, default=list)  # örn. ["search_documents", "get_exchange_rate"]
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_ms: Mapped[float] = mapped_column(Float)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)  # gerçek (lokal model → 0)
    reference_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)  # referans API modeliyle tahmini


class Employee(Base):
    """Kurgusal çalışan kaydı (text-to-SQL aracının sorguladığı tablo)."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(50))  # Çalıştığı ofis: İstanbul / Ankara / İzmir
    start_date: Mapped[date] = mapped_column(Date)  # İşe başlama tarihi (kıdem hesabı için)
    used_leave_days: Mapped[int] = mapped_column(Integer)  # Bu yıl kullanılan yıllık izin günü
    remote_days_per_week: Mapped[int] = mapped_column(Integer)  # Haftalık uzaktan çalışma günü


# Kurgusal örnek veri. Kıdemler el kitabındaki izin kademelerini (1–5 / 5–15 / 15+ yıl) kapsayacak şekilde seçildi.
SEED_EMPLOYEES = [
    Employee(id=1, full_name="Ayşe Yılmaz", department="Yazılım", city="İstanbul", start_date=date(2019, 3, 1), used_leave_days=8, remote_days_per_week=3),
    Employee(id=2, full_name="Mehmet Demir", department="Satış", city="Ankara", start_date=date(2023, 9, 15), used_leave_days=4, remote_days_per_week=1),
    Employee(id=3, full_name="Zeynep Kaya", department="İnsan Kaynakları", city="İstanbul", start_date=date(2008, 1, 7), used_leave_days=12, remote_days_per_week=2),
    Employee(id=4, full_name="Can Öztürk", department="Yazılım", city="İzmir", start_date=date(2016, 6, 20), used_leave_days=20, remote_days_per_week=3),
    Employee(id=5, full_name="Elif Şahin", department="Finans", city="İstanbul", start_date=date(2025, 2, 3), used_leave_days=2, remote_days_per_week=0),
    Employee(id=6, full_name="Burak Arslan", department="Satış", city="İzmir", start_date=date(2011, 11, 1), used_leave_days=15, remote_days_per_week=2),
]


@lru_cache
def get_engine() -> Engine:
    """Veritabanı bağlantı havuzu (uygulama boyunca bir tane)."""
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        # SQLite dosyasının klasörü yoksa oluştur (örn. data/)
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    # pool_pre_ping: havuzdaki bağlantı kopmuşsa kullanmadan önce fark et (Postgres yeniden başlarsa)
    return create_engine(url, pool_pre_ping=True)


def init_db(engine: Engine | None = None) -> None:
    """Tabloları oluşturur (yoksa) ve çalışan tablosu boşsa örnek veriyi ekler. Tekrar çağrılması güvenlidir."""
    engine = engine or get_engine()
    Base.metadata.create_all(engine)  # Var olan tablolara dokunmaz
    with Session(engine) as session:
        if session.scalar(select(Employee.id).limit(1)) is None:
            # merge: aynı id varsa günceller, yoksa ekler (SEED nesneleri tekrar kullanılabilsin diye kopya)
            for e in SEED_EMPLOYEES:
                session.merge(Employee(**{c.name: getattr(e, c.name) for c in Employee.__table__.columns}))
            session.commit()


def get_session() -> Iterator[Session]:
    """FastAPI dependency'si: istek başına bir oturum açar, istek bitince kapatır."""
    session = sessionmaker(bind=get_engine())()
    try:
        yield session
    finally:
        session.close()
