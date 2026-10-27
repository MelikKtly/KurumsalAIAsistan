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
ollama pull qwen3:8b   # ya da .env'deki LLM_MODEL (~5 GB)
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

Prompt versiyonlarını soru setinde karşılaştırmak (rapor `docs/`'a yazılır):

```bash
uv run python -m scripts.eval_prompts --versions v1 v2
```

Golden set'i (geliştirmede kullanılmamış 15 soru) üretim ayarlarıyla çalıştırmak:

```bash
uv run python -m scripts.run_golden
```

Groundedness hakeminin güvenilirliğini ölçmek:

```bash
uv run python -m scripts.eval_groundedness
```

Kaynaklı cevaplar varsayılan olarak ikinci bir LLM çağrısıyla (hakem) bağlama göre doğrulanır; bu, kaynaklı cevapların süresini yaklaşık ikiye katlar (ölçülen hakem süresi p50 ~7 sn). Kapatmak için `.env`'de `GROUNDEDNESS_CHECK=false`.

Her `/ask` isteğinin adım adım süresi, token kullanımı ve maliyet tahmini (`app/pricing.yaml` fiyatlarıyla) API cevabında (`metrics`) döner ve `logs/requests.jsonl`'a yazılır. Özet için:

```bash
uv run python -m scripts.log_stats            # p50/p95 süreler, ortalama token, maliyet projeksiyonu, cevap türleri
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
  evaluation/  # Cevapların kural tabanlı puanlanması
  prompts/     # Versiyonlu prompt dosyaları (rag/v1.yaml, rag/v2.yaml)
  config.py    # .env tabanlı ayarlar
data/pdfs/     # Kaynak PDF'ler (git'e girmez)
logs/          # İstek ölçümleri (requests.jsonl, git'e girmez)
data/eval/     # Değerlendirme soru seti (questions.yaml)
data/samples/  # Test için kurgusal örnek PDF (scripts/create_sample_pdf.py ile üretilir)
scripts/       # Yardımcı betikler
tests/
```
