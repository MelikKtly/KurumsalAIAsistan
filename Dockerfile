# FastAPI uygulamasının imajı (Faz 4.7). Ollama imaja dahil DEĞİLDİR: bilgisayardaki Ollama kullanılır.
FROM python:3.12-slim

# uv: bağımlılıkları uv.lock'taki tam sürümlerle kurmak için (lokal ortamla birebir aynı)
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv

WORKDIR /app

# Önce sadece bağımlılık dosyaları kopyalanır: kod değişince bu katman önbellekten gelir,
# bağımlılıklar (torch dahil) yeniden kurulmaz → yeniden derleme saniyeler sürer.
COPY pyproject.toml uv.lock ./
# --no-dev: test araçları imaja girmez; --frozen: uv.lock dışına çıkılmaz.
# Linux'ta torch'un CPU sürümü kurulur (pyproject.toml → tool.uv.sources).
RUN uv sync --frozen --no-dev --no-install-project

# Uygulama kodu ve örnek veri
COPY app ./app
COPY scripts ./scripts
COPY data/samples ./data/samples

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models

EXPOSE 8000
# --host 0.0.0.0: konteyner dışından (bilgisayarınızdan) erişilebilsin
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
