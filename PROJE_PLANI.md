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

Bu faz bitince elinde demo değil, kurulumu, testi ve dokümantasyonu olan, CV'ye konabilecek tam bir servis var.

## Claude Code ile Devam Etme Notları

Claude Code yeni bir oturumda bu konuşmanın geçmişini bilmiyor, o yüzden bu döküman onunla aran daki bağlantı görevi görüyor.

- Yeni bir Claude Code oturumu açtığında bu dokümanın içeriğini (özellikle Teknoloji Yığını ve Faz 1 adımları) context olarak yapıştır ya da özetle
- Faz 1'i bitirmeden Faz 2'ye geçmeye çalışma — her faz kendi başına bir checkpoint
- Bir adımda takılırsan, o adımı daha küçük parçalara böl (örn. "chunking çalışıyor mu" ayrı bir test adımı olabilir)
- İlerledikçe bu dokümanı güncelleyelim: hangi faz bitti, hangi kararlar alındı, neyin değiştirildiği buraya eklenebilir

## İlerleme ve Kararlar

### Faz 1 durumu

- [x] 1. Proje iskeleti — `uv` + Python 3.12, `app/{ingestion,retrieval,api}`, `.env` tabanlı ayarlar (`app/config.py`)
- [x] 2. PDF yükleme — `app/ingestion/loader.py` (doğrudan `pypdf`), test için kurgusal İK el kitabı (`data/samples/`)
- [x] 3. Chunking — `RecursiveCharacterTextSplitter`, 1000 karakter / 150 örtüşme
- [x] 4. Embedding + Chroma — `scripts/ingest.py`, sabit chunk ID'leri ile tekrar yüklemede kopya oluşmaz
- [x] 5. Retrieval — `app/retrieval/retriever.py`, cosine uzaklığı skoruyla top-k; `scripts/search.py` ile LLM'siz deneme
- [x] 6. RAG chain — `app/retrieval/rag.py` (LCEL: prompt | ChatOllama | parser), numaralı context + `[n]` atıfları; `scripts/ask.py`
- [x] 7. `POST /ask` — `app/api/main.py`, Pydantic istek/cevap şeması, Ollama kapalıysa 503, testlerde dependency override
- [x] 8. Elle test — 18 soru, `scripts/manual_test.py`; sonuçlar [docs/faz1_elle_test.md](docs/faz1_elle_test.md): içerik 12/18 doğru, retrieval recall@4 13/14

- [x] 9. *(Ek adım)* Sohbet arayüzü — `GET /`, tek dosya HTML/JS (`app/api/static/index.html`), `/ask`'i çağırır, tıklanabilir `[n]` atıfları ve kaynak kartları
- [x] 10. *(Ek adım)* `qwen3:8b`'ye geçiş + kurallı prompt (selamlaşma / konu dışı / dokümanda yok için sabit cevaplar) — karşılaştırma: [docs/faz1_elle_test.md](docs/faz1_elle_test.md#model-ve-prompt-karşılaştırması)

**Faz 1 tamamlandı (23 Ekim 2026).**

### Alınan kararlar

| Konu | Karar | Neden |
| --- | --- | --- |
| LLM | Ollama, `qwen3:8b` (önce `qwen3:1.7b`) | Ücretsiz, lokal. 1.7B uyduruyor, atıfları karıştırıyor ve kurallı promptta çıkarımı bozuluyordu; 8B ile içerik doğruluğu 12→16/18, konu dışı mesajlar 0→8/8, ama ~4 kat yavaş (~6.6 sn). Gerekirse ileride Claude API'ye geçilebilir |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2` | Lokal, ücretsiz, Türkçe destekli |
| PDF okuma | `pypdf` (LangChain `PyPDFLoader` yerine) | `langchain-community` sunset edildi |
| Frontend | FastAPI'nin sunduğu tek sayfa HTML/JS, kütüphanesiz | Odak backend+AI; ayrı frontend projesi gerektirmez, kendi API'mizi tüketir |
| Gerçek PDF'ler | `data/pdfs/` git'e girmez | Kurumsal belgeler repoya sızmasın |

### Notlar

- Embedding modeli değişirse Chroma koleksiyonu baştan yeniden oluşturulmalı.
- Retrieval zayıflığı: "Evden kaç gün çalışabilirim?" sorusunda Uzaktan Çalışma chunk'ı 2. sırada geldi → Faz 2+ reranking adayı.
- Büyük chunk'lar konuları karıştırıyor: chunk 4 (Eğitim + Yan Haklar + Bilgi Güvenliği) şifre sorusunda 2. sırada kaldı → daha küçük chunk veya başlık bazlı bölme denenebilir.
- Cevabı dokümanda olmayan soruda ("CEO kim?") en iyi uzaklık ~0.70, ilgili sorularda ~0.34–0.47 → Faz 2'deki "bilmiyorum" fallback'i için uzaklık eşiği adayı. **Güncelleme (8. adım):** Cevabı olan bazı sorularda da uzaklık 0.83–0.84 çıktı; eşik tek başına yetmez, groundedness kontrolü gerekli.
- `qwen3:1.7b` cevap içeriğinde doğru, ama `[n]` atıflarında hatalı: "[K1]" gibi uydurma format veya yanlış numara ([2] yerine [4]). → **Çözüldü:** 8B'ye geçildi.
- "Nasılsın?" gibi mesajlara doküman özeti dönüyordu → kurallı prompt ile çözüldü. Denenen alternatifler (1.7B ile LLM sınıflandırıcı: 10/26; embedding yönlendirici: 28/30) raporda.
- "Standart çalışma saatleri" sorusunda doğru chunk ilk 4'e girmiyor (her modelde yanlış) → retrieval/chunking sorunu, Faz 2+.
