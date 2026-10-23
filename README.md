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
# 1. PDF'leri vektör veritabanına yükle
uv run python -m scripts.ingest data/samples/ornek_ik_el_kitabi.pdf

# 2. API'yi başlat (Ollama açık olmalı)
uv run uvicorn app.api.main:app --reload
```

- Sohbet arayüzü: http://localhost:8000/
- Swagger (API dokümantasyonu): http://localhost:8000/docs

```bash
curl -X POST localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"question": "Kıdemim 7 yıl, kaç gün yıllık iznim var?"}'
```

```json
{
  "question": "Kıdemim 7 yıl, kaç gün yıllık iznim var?",
  "answer": "Kıdeminiz 7 yıl ise, yıllık izin hakkınız 20 iş günüdür. [1]",
  "sources": [
    {"ref": 1, "source": "ornek_ik_el_kitabi.pdf", "page": 2, "chunk_id": 2, "score": 0.3853, "snippet": "4. Yıllık İzin..."}
  ]
}
```

API olmadan komut satırından denemek için:

```bash
uv run python -m scripts.search "soru"   # sadece retrieval
uv run python -m scripts.ask "soru"      # retrieval + LLM
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
