# Multi-Agent (Supervisor + Worker) Değerlendirmesi — Faz 3.7

**Tarih:** 2026-10-27 · **Model:** `qwen3:8b` · **Supervisor promptu:** `supervisor/v2` · **Worker:** LangGraph agent, `agent/v3`
**Görev seti:** `data/eval/agent_tasks.yaml` — 15 görevin **ilk 11'i** ölçüldü (aşağıdaki "Kararlılık" bölümüne bakın)
**Yeniden üretmek için:** `uv run python -m scripts.eval_agent --agent multi --out docs/agent_multi.md`

## Özet: aynı 11 görevde tek-agent ile karşılaştırma

| Ölçüt | Tek-agent (LangGraph, agent/v3) | Multi-agent (supervisor + worker) |
| --- | --- | --- |
| **Görev başarısı** | **10/11** | 8/11 |
| Ortalama süre | **67 sn** | 126 sn (~1.9×) |
| Ortalama LLM çağrısı | **2.0** | 4.1 |
| Ortalama token | **4.279** | 5.853 (+%37) |
| Kararlılık | Tüm çalıştırmalarda sorunsuz | 2 değerlendirme çalıştırmasının ikisinde de süreç dondu |

Tek-agent sonuçları: [agent_graph_v3_15.md](agent_graph_v3_15.md) (aynı görevler).

## Görev bazında

| id | Görev | Multi-agent | Not |
| --- | --- | --- | --- |
| a01–a05 | Tek araçlı (doküman / kur) | ✅ ×5 | Her biri ~65–78 sn (tek-agent ~25–60 sn) |
| a06 | Yurt dışı harcırah kaç TL | ❌ | Hesap doğru (4.163,48 TL) ama son cevapta doküman değeri (75 €) yok: supervisor özetlerken kaynağı düşürdü |
| a07 | Konaklama limiti kaç Euro | ✅ | 222 sn |
| a08 | Eğitim bütçesi kaç dolar | ✅ | **458 sn**, adım limitine ulaştı (aşağıda iz) |
| a09–a10 | Selamlaşma | ✅ ×2 | Supervisor doğrudan bitirdi (8–11 sn) |
| a11 | Yurt içi / yurt dışı harcırah karşılaştırması | ❌ | Son cevapta doküman değerleri eksik (yalnızca TL karşılıkları) |

## a08'in adım adım izi: koordinasyon hataları

```
supervisor tur 1 → delegate: "Şirket dokümanlarında yıllık eğitim bütçesini belirleyen maddeleri bul..."
worker           → araç ÇAĞIRMADAN cevap verdi                     (213 sn boşa)
supervisor tur 2 → delegate: aynı görev tekrar
worker           → search_documents                                (110 sn)
supervisor tur 3 → delegate: "Güncel EUR/TRY kurunu al ve 15.000 TL'yi EURO'ya çevir"   ← soru DOLAR soruyordu
worker           → get_exchange_rate                               (67 sn)
supervisor tur 4 → finish
```

Supervisor ile worker arasındaki her devir yeni bir hata noktası: worker'ın aracı kullanmaması, görevin tekrarlanması, talimat aktarılırken bilgi kaybı ("dolar" → "Euro") ve son özette doküman kaynaklarının düşmesi (a06, a11).

## Kararlılık: iç içe graf donması

İki değerlendirme çalıştırmasında da süreç bir görevin ortasında dondu: Ollama boştaydı, ana thread bir kilit bekliyordu, LLM okuma zaman aşımı (120 sn) tetiklenmedi. Tek-agent onlarca görevde hiç donmadı. Yapısal fark: multi-agent'ta bir LangGraph grafiği (supervisor) düğümünün içinden **ikinci bir LangGraph grafiğini** (worker) çalıştırıyor. En güçlü şüphe, bu iç içe çalıştırmanın LangGraph'ın thread havuzunda kilitlenmeye (deadlock) yol açması — kesin kök neden bulunmadı. Çözüm adayları: worker'ı alt graf (subgraph) olarak eklemek veya worker'ı ayrı bir thread yerine aynı yürütücüde çalıştırmak.

## Sonuç

Bu boyuttaki görevler (1–3 araç çağrısı) için **tek-agent daha hızlı, daha isabetli ve daha kararlı**. Multi-agent; birbirinden bağımsız çok sayıda alt görev, farklı uzmanlık gerektiren roller veya paralel çalışma olduğunda değer katar — burada yalnızca ek LLM çağrısı ve hata noktası getirdi. Bu yüzden `/agent` endpoint'i tek-agent'ı (LangGraph) kullanıyor; multi-agent kodu deney olarak repoda duruyor.
