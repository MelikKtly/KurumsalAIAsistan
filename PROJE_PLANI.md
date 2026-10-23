# Kurumsal AI Asistanı — Proje Planı

Oct 22, 2026 · @Melik

## Proje Özeti

Dağınık kurumsal veri kaynaklarını (PDF, SQL, web) doğal dilde sorgulanabilir hale getiren bir RAG + Agent platformu kuruyoruz. Sistem bir soruya ilgili kaynaklardan bilgiyi bulup kaynak göstererek cevap veriyor; daha karmaşık isteklerde bir agent devreye girip birden fazla aracı (SQL sorgusu, vektör arama, dış API) sırayla kullanarak görevi tamamlıyor.

Hedef: FastAPI (backend) ile LangChain/LangGraph (AI) mühendisliğini tek bir üründe birleştirip, hedeflenen senior AI engineer ilanının gereksinimlerini junior seviyesinden adım adım, küçültülmüş bir kapsamla karşılamak.

## Teknoloji Yığını

| Katman | Teknoloji | Amaç |
| --- | --- | --- |
| Backend servisi | FastAPI | API katmanı, endpoint'ler |
| RAG orkestrasyonu | LangChain | Document loader, chunking, retrieval chain |
| Agent orkestrasyonu | LangGraph | Çok adımlı planlama, tool-use, single/multi-agent |
| Vektör DB | Chroma (başlangıç), Qdrant/pgvector (sonra) | Embedding depolama ve arama |
| İlişkisel DB | PostgreSQL + SQLAlchemy | SQL kaynağı, metadata, review geçmişi |
| Embedding | OpenAI/Claude ya da sentence-transformers | Metni vektöre çevirme |
| Reranking | Cross-encoder (açık kaynak) ya da Cohere rerank | Retrieval kalitesini artırma |
| İzleme/Eval | LangSmith | Latency, maliyet, doğruluk takibi |
| Test | pytest | Test edilebilirlik |

## Yol Haritası

&#91;embedded content: 4 faz · junior'dan backend+AI engineer'a\]

Her faz kendi başına tamamlanabilir bir kazanım; bir sonraki faza geçmeden önce o fazın geçidi sağlanmalı.

## Faz 1 — İlk Adımlar (Başlangıç Noktası)

Küçültülmüş kapsam: tek veri kaynağı (PDF), basit bir uçtan uca RAG akışı. Hedef, çalışan bir MVP'yi mümkün olduğunca hızlı görmek.

1. Proje iskeleti: Python sanal ortam, FastAPI, LangChain, Chroma kurulumu; klasör yapısı (`ingestion/`, `retrieval/`, `api/`)
2. Bir PDF dosyasını LangChain document loader ile yükleme
3. Metni parçalara ayırma (chunking) — önce tek bir stratejiyle (recursive character splitter) başla
4. Parçaları embedding'e çevirip Chroma'ya yazma
5. Basit bir retrieval fonksiyonu: soru geldiğinde en ilgili parçaları geri getirme
6. Bulunan parçaları LLM'e context olarak verip cevap üretme (basit bir RAG chain)
7. Bunu tek bir FastAPI endpoint'i (`POST /ask`) olarak dışarı açma
8. Birkaç soruyla elle test etme — cevaplar mantıklı mı, kaynak gösteriyor mu?

Bu sekiz adım bitince elinde zaten çalışan, gösterilebilir bir RAG sistemi var. Reranking, çoklu kaynak ve eval katmanı sonraki iterasyonlarda eklenir.

## Claude Code ile Devam Etme Notları

Claude Code yeni bir oturumda bu konuşmanın geçmişini bilmiyor, o yüzden bu döküman onunla aran daki bağlantı görevi görüyor.

- Yeni bir Claude Code oturumu açtığında bu dokümanın içeriğini (özellikle Teknoloji Yığını ve Faz 1 adımları) context olarak yapıştır ya da özetle
- Faz 1'i bitirmeden Faz 2'ye geçmeye çalışma — her faz kendi başına bir checkpoint
- Bir adımda takılırsan, o adımı daha küçük parçalara böl (örn. "chunking çalışıyor mu" ayrı bir test adımı olabilir)
- İlerledikçe bu dokümanı güncelleyelim: hangi faz bitti, hangi kararlar alındı, neyin değiştirildiği buraya eklenebilir
