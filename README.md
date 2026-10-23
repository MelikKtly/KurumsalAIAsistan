# Kurumsal AI Asistanı

Dağınık kurumsal veri kaynaklarını (PDF, SQL, web) doğal dilde sorgulanabilir hale getiren RAG + Agent platformu.

Detaylı yol haritası: [PROJE_PLANI.md](PROJE_PLANI.md)

## Faz 1 — Teknoloji

- **API:** FastAPI
- **RAG:** LangChain
- **Vektör DB:** Chroma
- **Embedding:** sentence-transformers (lokal)
- **LLM:** Ollama (lokal)

## Kurulum

```bash
uv sync
cp .env.example .env
ollama pull qwen3:1.7b   # ya da .env'deki LLM_MODEL
```

## Çalıştırma

```bash
uv run uvicorn app.api.main:app --reload
```

## Test

```bash
uv run pytest
```

## Klasör Yapısı

```
app/
  ingestion/   # PDF yükleme, chunking, embedding, Chroma'ya yazma
  retrieval/   # Arama ve RAG chain
  api/         # FastAPI endpoint'leri
  config.py    # .env tabanlı ayarlar
data/pdfs/     # Kaynak PDF'ler (git'e girmez)
data/samples/  # Test için kurgusal örnek PDF (scripts/create_sample_pdf.py ile üretilir)
scripts/       # Yardımcı betikler
tests/
```
