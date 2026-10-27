import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.agent.sql_tool import run_readonly_query, validate_sql
from app.db import Employee, init_db


@pytest.fixture
def engine(tmp_path):
    # Her test için ayrı, geçici SQLite veritabanı (örnek çalışanlarla dolu)
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    return engine


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT full_name FROM employees",
        "select * from employees where city = 'İzmir';",  # sondaki ; serbest
        "WITH t AS (SELECT * FROM employees) SELECT full_name FROM t JOIN employees e ON e.id = t.id",
    ],
)
def test_valid_selects(sql):
    # WITH ile tanımlanan geçici ad ("t") gerçek tablo sayılmamalı
    assert validate_sql(sql) is None


@pytest.mark.parametrize(
    "sql, reason",
    [
        ("DELETE FROM employees", "SELECT"),
        ("SELECT 1; DROP TABLE employees", "tek bir"),
        ("SELECT * FROM employees WHERE 1=1 UNION SELECT * FROM query_logs", "erişim yok"),
        ("SELECT * FROM query_logs", "erişim yok"),
        ("SELECT * FROM employees; ", None),  # sondaki ; + boşluk geçerli
        ("PRAGMA table_info(employees)", "SELECT"),
        # CTE adı izinli tablo kılığına sokulup yasak tablo okunamaz
        ("WITH employees AS (SELECT * FROM query_logs) SELECT * FROM employees", "erişim yok"),
    ],
)
def test_validation_rules(sql, reason):
    error = validate_sql(sql)
    if reason is None:
        assert error is None
    else:
        assert error is not None and reason in error


def test_query_returns_table_text(engine):
    out = run_readonly_query("SELECT full_name, city FROM employees WHERE full_name LIKE '%Ayşe%'", engine)
    assert out.splitlines() == ["full_name | city", "Ayşe Yılmaz | İstanbul"]


def test_bad_sql_returns_error_text_not_exception(engine):
    out = run_readonly_query("SELECT olmayan_sutun FROM employees", engine)
    assert out.startswith("HATA: SQL çalıştırılamadı")


def test_database_level_read_only(engine):
    # Doğrulamayı atlayıp doğrudan yazma denensin: salt-okunur bağlantı engellemeli
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA query_only = ON")
        with pytest.raises(Exception):
            conn.exec_driver_sql("DELETE FROM employees")
        conn.exec_driver_sql("PRAGMA query_only = OFF")
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Employee)) == 6  # hiçbir satır silinmedi


def test_init_db_is_idempotent(engine):
    init_db(engine)  # İkinci kez çağrı: tekrar veri eklememeli
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Employee)) == 6
