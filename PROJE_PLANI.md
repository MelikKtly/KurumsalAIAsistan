# Kurumsal AI Asistanı — Proje Planı

Oct 22, 2026 · @Melik

## Proje Özeti

Dağınık kurumsal veri kaynaklarını (PDF, SQL, web) doğal dilde sorgulanabilir hale getiren bir RAG + Agent platformu kuruyoruz. Sistem bir soruya ilgili kaynaklardan bilgiyi bulup kaynak göstererek cevap veriyor; daha karmaşık isteklerde bir agent devreye girip birden fazla aracı (SQL sorgusu, vektör arama, dış API) sırayla kullanarak görevi tamamlıyor.

Hedef: FastAPI (backend) ile LangChain/LangGraph (AI) mühendisliğini tek bir üründe birleştirmek; kapsamı küçültülmüş ama uçtan uca çalışan bir sistemi adım adım kurmak.

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

## Faz 2 — Kalite Katmanı (Detaylı Adımlar)

Faz 1'deki RAG çekirdeğini güvenilirlik ve ölçülebilirlik tarafıyla güçlendiriyoruz.

1. Sistem promptunu ayrı bir dosyada toplayıp LangChain `PromptTemplate` ile yapılandır — kod içine gömülmüş string olmasın
2. En az iki farklı prompt versiyonu yaz, aynı sorularda karşılaştır (örn. "sadece context'e dayan" talimatı olan/olmayan)
3. "Bilmiyorum" fallback'i ekle: context'te cevap yoksa model uydurmasın, bunu açıkça söylesin
4. Groundedness kontrolü: üretilen cevabı kullanılan context'le karşılaştırıp "bu cevap context'e dayanıyor mu" diye ikinci bir LLM çağrısıyla doğrula
5. Her isteğin latency ve token sayısını logla
6. Token sayısı × model fiyatından yaklaşık maliyeti hesapla, her istekle birlikte kaydet
7. (Opsiyonel) LangSmith'e bağlan, trace'leri orada incele
8. 10-15 soruluk küçük bir "golden set" oluştur, cevapları elle değerlendirip bir doğruluk notu tut — Faz 4'teki otomatik eval'in temeli olacak

Bu faz bitince sisteminin ne kadar güvenilir, ne kadar hızlı ve ne kadara mal olduğunu ölçebiliyorsun.

## Faz 3 — Agent Katmanı (Detaylı Adımlar)

Artık statik soru-cevaptan çıkıp modele araç kullandırıp çok adımlı görevler yaptırıyoruz.

1. İlk aracı tanımla: Faz 1'deki vektör arama fonksiyonunu bir "tool" olarak sar
2. Claude'un function calling özelliğiyle tek bir aracı çağırabilen basit bir agent yaz (henüz LangGraph yok, tek adımlı tool-use)
3. İkinci bir araç ekle (örn. bir REST API çağrısı) — modelin iki araç arasında doğru seçim yapıp yapmadığını gözlemle
4. LangGraph'a geç: basit bir state machine kur (plan → tool çağır → sonucu değerlendir → bitir ya da tekrar et)
5. Çok adımlı bir görev senaryosu tasarla (örn. "dokümanlardan bilgi bul, başka bir kaynaktan veri çek, ikisini karşılaştırıp özetle") ve agent'ın adım adım çözmesini sağla
6. Her adımı logla (hangi tool çağrıldı, hangi girdiyle, ne sonuç döndü) — debug ve eval için şart
7. Basit bir "supervisor + tek worker" multi-agent denemesi yap, aynı görevi tek-agent versiyonuyla karşılaştır
8. Başarısız/döngüye giren senaryoları not et, agent'a maksimum adım limiti koy

Bu faz bitince modelin sadece soru cevaplamadığı, görev planlayıp araç kullanarak iş yaptığı çalışan bir agent sistemin var.

## Faz 4 — Servis ve Test (Detaylı Adımlar)

Artık tüm parçaları gerçek, test edilebilir bir servise dönüştürüyoruz.

1. FastAPI üzerinden üç endpoint aç: `/ask` (RAG), `/agent` (agent görevi), `/health`
2. PostgreSQL ekle: sorgu geçmişini, kullanılan tool'ları, maliyet/latency metriklerini kaydet
3. SQL ve vektör DB'yi aynı sistemde birlikte kullan (örn. text-to-SQL aracı Postgres'e, retrieval aracı Chroma'ya gidiyor)
4. Yapılandırılmış logging ekle (JSON formatlı loglar, log seviyeleri)
5. pytest ile temel testler yaz: retrieval doğru chunk'ı buluyor mu, agent doğru tool'u seçiyor mu (mock LLM yanıtlarıyla)
6. Faz 2'deki golden set'i otomatik çalıştıran bir eval scripti yaz, GitHub Actions'a ekle
7. Docker Compose ile tüm sistemi (FastAPI + Postgres + Chroma) tek komutla ayağa kaldır
8. README yaz: mimari diyagram, kurulum adımları, örnek istek/cevap, ölçülmüş sonuçlar (latency, maliyet, golden set doğruluk oranı)

Bu faz bitince elinde demo değil, kurulumu, testi ve dokümantasyonu olan tam bir servis var.

## İlerleme ve Kararlar

### Faz 1 durumu

- [x] 1. Proje iskeleti — `uv` + Python 3.12, `app/{ingestion,retrieval,api}`, `.env` tabanlı ayarlar (`app/config.py`)
- [x] 2. PDF yükleme — `app/ingestion/loader.py` (doğrudan `pypdf`), test için kurgusal İK el kitabı (`data/samples/`)
- [x] 3. Chunking — `RecursiveCharacterTextSplitter`, 1000 karakter / 150 örtüşme
- [x] 4. Embedding + Chroma — `scripts/ingest.py`, sabit chunk ID'leri ile tekrar yüklemede kopya oluşmaz
- [x] 5. Retrieval — `app/retrieval/retriever.py`, cosine uzaklığı skoruyla top-k; `scripts/search.py` ile LLM'siz deneme
- [x] 6. RAG chain — `app/retrieval/rag.py` (LCEL: prompt | ChatOllama | parser), numaralı context + `[n]` atıfları; `scripts/ask.py`
- [x] 7. `POST /ask` — `app/api/main.py`, Pydantic istek/cevap şeması, Ollama kapalıysa 503, testlerde dependency override
- [x] 8. Elle test — 18 soru (sonradan `data/eval/questions.yaml`'a taşındı); sonuçlar [docs/faz1_elle_test.md](docs/faz1_elle_test.md): içerik 12/18 doğru, retrieval recall@4 13/14

- [x] 9. *(Ek adım)* Sohbet arayüzü — `GET /`, tek dosya HTML/JS (`app/api/static/index.html`), `/ask`'i çağırır, tıklanabilir `[n]` atıfları ve kaynak kartları
- [x] 10. *(Ek adım)* `qwen3:8b`'ye geçiş + kurallı prompt (selamlaşma / konu dışı / dokümanda yok için sabit cevaplar) — karşılaştırma: [docs/faz1_elle_test.md](docs/faz1_elle_test.md#model-ve-prompt-karşılaştırması)

**Faz 1 tamamlandı (23 Ekim 2026).**

### Faz 2 durumu

- [x] 1. Prompt ayrı dosyada — `app/prompts/rag/<versiyon>.yaml`, `app/prompts/loader.py` ile `ChatPromptTemplate`'e çevrilir; değişken uyuşmazlığında hata verir. Aktif versiyon `.env`'de `RAG_PROMPT_VERSION`; cevapta `prompt_version` döner. v1 = Faz 1.6 sade prompt, v2 = Faz 1.10 kurallı prompt
- [x] 2. Prompt versiyonlarını karşılaştırma — `scripts/eval_prompts.py`, 29 soruluk set (`data/eval/questions.yaml`), kural tabanlı puanlama (`app/evaluation/scoring.py`). Sonuç [docs/prompt_karsilastirma.md](docs/prompt_karsilastirma.md): v1 %76, v2 %97 (şirket sorularında eşit; fark selamlaşma/konu dışında)
- [x] 3. "Bilmiyorum" fallback'i — v2 promptunun sabit cevapları + kodda `classify_answer()`: API cevabında `answer_type` (`answered` / `not_found` / `off_topic` / `uncited`) ve kaynak başına `cited`. Arayüz yalnızca `answered` cevaplarda kaynak gösterir, atıf yapılmayan kaynakları soluklaştırır
- [x] 4. Groundedness kontrolü — `app/retrieval/groundedness.py` (LLM-as-judge, `app/prompts/groundedness/v1.yaml`). Hakem desteksiz iddiaları listeler, karar kodda verilir (`grounded = not unsupported_claims`). `.env`: `GROUNDEDNESS_CHECK` (varsayılan **açık**; yalnızca kaynaklı cevaplarda çalışır; ölçülen ek süre p50 ~7 sn → kaynaklı cevaplarda süre ~2 katı, bkz. Faz 2.5). Hakem 22 vakalık sette ölçüldü ([docs/groundedness_degerlendirme.md](docs/groundedness_degerlendirme.md)): 3 iterasyonda uydurma yakalama 6/12 → 8/12 → 12/12, yanlış alarm 0/10
- [x] 5. Latency + token loglama — `app/observability.py`: adım adım süre (retrieval / üretim / hakem / toplam) ve LLM çağrısı başına girdi/çıktı token. API cevabında `metrics`, her istek `logs/requests.jsonl`'a bir JSON satırı; özet: `scripts/log_stats.py`. İlk ölçüm (29 soru, hakem açık): toplam p50 10.5 sn / p95 22.1 sn; üretim p50 7.1 sn, hakem p50 7.4 sn, retrieval p50 0.2 sn; istek başına ~2.400 token (%98'i girdi)
- [x] 6. Maliyet hesabı — `app/pricing.yaml` (model fiyatları, 1M token başına) + `app/cost.py`. Her istekte gerçek maliyet (Ollama → $0) ve referans API modeliyle tahmini maliyet (`.env`: `COST_REFERENCE_MODEL`, varsayılan `claude-sonnet-5-5`); API cevabında `metrics.cost`, logda da var. `log_stats.py` loglanan kullanımı tüm API modelleriyle fiyatlar: istek başı ~Opus 5.5 $0.0104 / Sonnet 5.5 $0.0052 / Haiku 5.5 $0.00026 (hakem dahil; qwen tokenizer'ına göre yaklaşık)
- [~] 7. (Opsiyonel) LangSmith — **atlandı** (kullanıcı kararı): kendi ölçüm/log sistemimiz (2.5–2.6) yeterli ve kurumsal veri dışarı çıkmıyor. Gerekirse `.env.example`'daki `LANGSMITH_*` satırlarıyla kod değişikliği olmadan açılabilir
- [x] 8. Golden set — `data/eval/golden_set.yaml`: geliştirmede hiç kullanılmamış 15 soru + referans cevaplar; `scripts/run_golden.py` üretim ayarlarıyla çalıştırır. Elle değerlendirme [docs/golden_set_v1.md](docs/golden_set_v1.md): **12/15 tam doğru (%80)**, 1 kısmen, 2 yanlış; uydurma 0/15. Yeni hata türü: dokümanda olmayan şirket soruları (ciro, kreş) "konu dışı" diye reddediliyor
- [x] 9. *(Ek adım)* Golden set bulgusuna göre v3 prompt denendi, **geri alındı**: geliştirme setinde v2 30/33, v3 28/33 ([docs/prompt_karsilastirma_v2_v3.md](docs/prompt_karsilastirma_v2_v3.md)). Puanlama sıkılaştırıldı (konu dışı sanma, soru tekrarı, Markdown) ve geliştirme setine 4 yeni soru eklendi. "Annelik izni" sorusunda her iki prompt da uydurdu; hakem yakaladı

**Faz 2 tamamlandı (27 Ekim 2026).**

### Faz 3 durumu

- [x] 1. Vektör arama araç olarak — `app/agent/tools.py`: `search_documents` (Faz 1 retrieval'ı `@tool` ile sarıldı)
- [x] 2. Tek araçlı, tek adımlı agent — `app/agent/simple_agent.py` (döngüsüz: karar → araç → cevap). LLM: Ollama `qwen3:8b` (ücretsiz; plandaki "Claude function calling" yerine). Bulgu: qwen3 düşünme modu kapalıyken araç çağıramıyor → agent için `get_agent_llm()` (reasoning=True)
- [x] 3. İkinci araç: `get_exchange_rate` (frankfurter.dev, ücretsiz/anahtarsız ECB kurları). `data/eval/agent_tasks.yaml` (10 görev) + `scripts/eval_agent.py`. Sonuç [docs/agent_simple.md](docs/agent_simple.md): **7/10** — tek araçlı/araçsız görevler 7/7, iki araç gerektiren görevler **0/3** (model ilk turda yalnızca doküman aramasını çağırıyor, kura 2. turda ihtiyaç duyuyor ama tek adımlı yapı izin vermiyor; bir denemede kuru uydurdu: 10,35 TRY). Ortalama 44.6 sn/görev
- [x] 4. LangGraph state machine — `app/agent/graph.py`: agent (planla/değerlendir) → tools (araç çağır) → agent döngüsü, `finalize` (limit dolunca araçsız son cevap). İlk ölçüm: 9/10 (tek adımlı 7/10). 12 görevde prompt karşılaştırması: v1 11/12, **v2 12/12** (görev başına 64 → 82 sn) ([v1](docs/agent_graph_v1.md), [v2](docs/agent_graph_v2.md)); varsayılan agent promptu v2
- [x] 5. Çok adımlı görev senaryosu — `agent_tasks.yaml`'a a11 (yurt içi/yurt dışı harcırah karşılaştırması, TL) ve a12 (3 günlük yurt dışı harcırah toplamı) eklendi; agent prompt v2 (araçları kendin çağır, sayıları yalnızca araç sonuçlarından al)
- [x] 6. Adım adım loglama — her LLM kararı (planlanan araçlar, süre, token) ve her araç çalışması (girdi, sonuç, süre) `trace` olarak; `logs/agent.jsonl`. a06 hatası bu izle bulundu: model kur aracını kendisi çağırmak yerine kullanıcıya "get_exchange_rate aracını kullanın" yazdı
- [x] 7. Supervisor + worker multi-agent — `app/agent/multi_agent.py`: supervisor (araçsız, yapılandırılmış karar: önce düşünce sonra karar) ↔ worker (LangGraph agent'ı); tur limiti, geçersiz çıktıda güvenli bitiş. **Karşılaştırma** ([docs/agent_multi.md](docs/agent_multi.md)), aynı 11 görev: multi 8/11 vs tek-agent **10/11**; 126 vs **67 sn**; 4.1 vs 2.0 LLM çağrısı. Koordinasyon hataları (worker araç kullanmadı, görev tekrarı, talimatta "dolar"→"Euro") ve iç içe LangGraph grafiğinde donma (muhtemel deadlock, kök neden bulunamadı) → `/agent` tek-agent kullanır
- [x] 8. Başarısız senaryolar, maksimum adım limiti — ayrıca multi-agent ölçümünde bir LLM isteği 5+ dk cevapsız kaldı (süreç dondu) → tüm LLM bağlantılarına okuma zaman aşımı (`LLM_READ_TIMEOUT_S`). Önceki: — `AGENT_MAX_STEPS` (6, finalize ile), multi-agent tur limiti, LangGraph `recursion_limit`. Gerçek ölçümde bulunan döngü: düşünme modunda bir görev tek LLM çağrısı içinde 11+ dk takıldı (adım limiti yakalayamaz) → `AGENT_MAX_OUTPUT_TOKENS=2048` (normal çağrı 100–500) + `done_reason="length"` tespiti (`stop_reason: output_limit`). Not: Ollama read timeout toplam süre sınırı değil (stream parçaları arası)

### Faz 4 durumu

- [x] 1. Endpoint'ler — `/ask`, `/agent` (LangGraph agent, adımlar + maliyet döner), `/health`
- [x] 2. Veritabanı — `app/db.py` (SQLAlchemy): `query_logs` (her /ask ve /agent isteği: soru, cevap, araçlar, süre, token, maliyet) + `employees`. `DATABASE_URL`: lokal SQLite, Docker'da PostgreSQL
- [x] 3. SQL + vektör DB birlikte — `app/agent/sql_tool.py`: `query_employees` text-to-SQL aracı (tek SELECT, tablo izin listesi, CTE kontrolü, veritabanı seviyesinde salt-okunur, 50 satır sınırı); agent prompt v3; `agent_tasks.yaml`'a a13–a15 (kural + kişi verisi)
- [x] 4. Yapılandırılmış logging — `app/logging_config.py`: JSON loglar stdout'a, `LOG_LEVEL`; her istek için request_id (X-Request-ID başlığı), süre, durum; agent araç çağrıları DEBUG, araç hataları WARNING, Ollama erişilemez ERROR
- [x] 5. pytest temel testler — toplam 109 test. Retrieval kalitesi (`tests/test_retrieval_quality.py`): gerçek embedding modeliyle geliştirme setinde recall@4 ≥ 15/17 ve anlamsal eşleşme örnekleri; model yoksa (CI) otomatik atlanır. Agent araç seçimi (mock LLM): üç aracın modele bağlanması, kişiye özgü soruda SQL → doküman akışı (`tests/test_graph_agent.py`), SQL güvenliği (`tests/test_sql_tool.py`)
- [x] 6. Golden set otomatik eval + GitHub Actions — `scripts/run_golden.py --min-pass N` kalite kapısı (eşik altında çıkış kodu 1; LLM gerektirdiği için lokalde). `.github/workflows/tests.yml`: her push'ta pytest (LLM'siz, ücretsiz kota içinde). Linux'ta CPU-only PyTorch (`tool.uv.sources`) → CI/Docker'da ~3 GB CUDA indirmesi yok
- [x] 7. Docker Compose — `Dockerfile` + `docker-compose.yml`: api + postgres:16 + chroma 1.5.9 (sunucu modu); Ollama bilgisayarda (`host.docker.internal`). Uçtan uca doğrulandı: konteynerden ingest → Chroma sunucusu, `/ask` (hakem dahil), `/agent` (doküman + kur, SQL), Postgres'e `query_logs` kaydı, JSON loglar. Postgres'te salt-okunur SQL koruması doğrulandı (`ReadOnlySqlTransaction`). Host portu 5433 (yerel PostgreSQL 5432'yi kullanıyor). İmaj ~2 GB
- [x] 8. README — mimari diyagram (Mermaid), teknoloji, ölçülmüş sonuçlar tablosu (RAG + agent), lokal ve Docker kurulumu, gerçek örnek istek/cevaplar, yapılandırma, değerlendirme komutları, proje yapısı, bilinen sınırlar

**Faz 4 tamamlandı — proje tamamlandı (27 Ekim 2026).**

### Alınan kararlar

| Konu | Karar | Neden |
| --- | --- | --- |
| LLM | Ollama, `qwen3:8b` (önce `qwen3:1.7b`) | Ücretsiz, lokal. 1.7B uyduruyor, atıfları karıştırıyor ve kurallı promptta çıkarımı bozuluyordu; 8B ile içerik doğruluğu 12→16/18, konu dışı mesajlar 0→8/8, ama ~4 kat yavaş (~6.6 sn). Gerekirse ileride Claude API'ye geçilebilir |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2` | Lokal, ücretsiz, Türkçe destekli |
| PDF okuma | `pypdf` (LangChain `PyPDFLoader` yerine) | `langchain-community` sunset edildi |
| Prompt yönetimi | Versiyonlu YAML dosyaları (`app/prompts/`) | Çok satırlı metin okunaklı; açıklama ve sabit cevaplar aynı dosyada; versiyonlar kod değişmeden `.env` ile seçilir ve karşılaştırılabilir |
| Groundedness kararı | LLM yalnızca desteksiz iddiaları listeler; `grounded` kodda türetilir | LLM kararı alanı ilk sıradayken düşünmeden karar veriyor, sonrakinde listeyle çelişen karar veriyordu (ölçüldü) |
| Maliyet (lokal model) | Gerçek maliyet $0 + referans API modeliyle tahmini maliyet | Ollama ücretsiz; plan "token × fiyat" istiyor → "API'ye geçersek ne öderiz" sorusunu cevaplamak için |
| Agent mimarisi | Tek-agent (LangGraph) | Multi-agent ölçümde daha yavaş (~1.9×), daha az isabetli (8/11 vs 10/11) ve kararsız (donma) |
| Agent prompt | v3 (SQL + kural birleştirme) | v2 ile 15 görevde eşit (13/15); v3 kişiye özgü sorularda doğru |
| Frontend | FastAPI'nin sunduğu tek sayfa HTML/JS, kütüphanesiz | Odak backend+AI; ayrı frontend projesi gerektirmez, kendi API'mizi tüketir |
| Gerçek PDF'ler | `data/pdfs/` git'e girmez | Kurumsal belgeler repoya sızmasın |

### Notlar

- Embedding modeli değişirse Chroma koleksiyonu baştan yeniden oluşturulmalı.
- Retrieval zayıflığı: "Evden kaç gün çalışabilirim?" sorusunda Uzaktan Çalışma chunk'ı 2. sırada geldi → Faz 2+ reranking adayı.
- Büyük chunk'lar konuları karıştırıyor: chunk 4 (Eğitim + Yan Haklar + Bilgi Güvenliği) şifre sorusunda 2. sırada kaldı → daha küçük chunk veya başlık bazlı bölme denenebilir.
- Cevabı dokümanda olmayan soruda ("CEO kim?") en iyi uzaklık ~0.70, ilgili sorularda ~0.34–0.47 → Faz 2'deki "bilmiyorum" fallback'i için uzaklık eşiği adayı. **Güncelleme (8. adım):** Cevabı olan bazı sorularda da uzaklık 0.83–0.84 çıktı; eşik tek başına yetmez, groundedness kontrolü gerekli.
- `qwen3:1.7b` cevap içeriğinde doğru, ama `[n]` atıflarında hatalı: "[K1]" gibi uydurma format veya yanlış numara ([2] yerine [4]). → **Çözüldü:** 8B'ye geçildi.
- "Nasılsın?" gibi mesajlara doküman özeti dönüyordu → kurallı prompt ile çözüldü. Denenen alternatifler (1.7B ile LLM sınıflandırıcı: 10/26; embedding yönlendirici: 28/30) raporda.
- **Uzaklık eşiğiyle "bilmiyorum" denemedi (Faz 2.3 kararı):** 29 soruda en iyi uzaklık — cevaplanabilir 0.25–0.84, dokümanda yok 0.51–0.83, selamlaşma 0.74–0.91, konu dışı 0.73–0.90. Geçerli soruları (spor 0.83, şifre 0.84) kaybetmeyen bir eşik (>0.84) yalnızca birkaç konu dışı mesajı yakalar ve "Nasılsın?"a (0.91) selam yerine "bilgi yok" dedirtir → kazanç küçük, risk büyük.
- "Standart çalışma saatleri" sorusunda doğru chunk ilk 4'e girmiyor (her modelde yanlış) → retrieval/chunking sorunu, Faz 2+.
