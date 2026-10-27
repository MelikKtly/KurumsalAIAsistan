# Agent Değerlendirmesi: `graph`

**Tarih:** 2026-10-27 · **Model:** `qwen3:8b` · **Prompt:** `agent/v2` · **Görev seti:** `data/eval/agent_tasks.yaml` (12 görev)  
**Yeniden üretmek için:** `uv run python -m scripts.eval_agent --agent graph --prompt v2 --out docs/agent_graph_v2.md`

| Ölçüt | Sonuç |
| --- | --- |
| **Görev başarısı** (doğru araçlar + beklenen bilgi) | **12/12** |
| Doğru araç seçimi | 12/12 |
| Beklenen bilgi cevapta | 12/12 |
| Ortalama LLM çağrısı | 2.2 |
| Ortalama süre | 81.6 sn |
| Ortalama token | 4356 |

| id | Soru | Beklenen araçlar | Çağrılan araçlar | Sonuç | Cevap |
| --- | --- | --- | --- | --- | --- |
| a01 | Babalık izni kaç gün? | search_documents | search_documents | ✅ | Babalık izni 10 gündür. [1] |
| a02 | Yıllık eğitim bütçem ne kadar? | search_documents | search_documents | ✅ | Yıllık eğitim bütçeniz 15.000 TL'dir. Bu tutar, [1] numaralı dokümanda belirtilmiştir. |
| a03 | Şifrem en az kaç karakter olmalı? | search_documents | search_documents | ✅ | Şifreler en az 12 karakter olmalı ve her 90 günde bir değiştirilmelidir. [2] |
| a04 | 1 Euro bugün kaç TL? | get_exchange_rate | get_exchange_rate | ✅ | 1 Euro bugün 55.513 TL'dir (tarih: 2026-10-27, kaynak: Avrupa Merkez Bankası). |
| a05 | 100 Amerikan doları kaç Euro eder? | get_exchange_rate | get_exchange_rate | ✅ | 100 USD, 89,69 Euro'ya eşittir (tarih: 2026-10-27, kaynak: Avrupa Merkez Bankası). |
| a06 | Yurt dışı günlük yemek harcırahım kaç TL eder? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt dışı günlük yemek harcırahı **75 Euro**'dur ([1] kaynak). **55.513 TRY** kuru kullanılarak hesaplanan tu… |
| a07 | Yurt içi gecelik konaklama limiti kaç Euro'ya denk geliyor? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt içi gecelik konaklama üst limiti **4.000 TL**'dir. Bu tutar, 2026-10-27 tarihli döviz kuru (1 TRY = 0.01… |
| a08 | Yıllık eğitim bütçem kaç dolar eder? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yıllık eğitim bütçeniz 15.000 TL'dir. [1] Bu tutar dolar cinsinden 301.28 USD'ye eşittir (kuru: 1 TRY = 0.020… |
| a09 | Merhaba, nasılsın? | — | — | ✅ | İyi günler, ben Sen Örnek Teknoloji A.Ş.'nin çalışanlarına hizmet eden bir asistanım. Size nasıl yardımcı ola… |
| a10 | Teşekkürler, çok yardımcı oldun. | — | — | ✅ | Çok mutluyum! Her zaman yardımcı olmaya hazırım. |
| a11 | Yurt dışı günlük yemek harcırahı ile yurt içi günlük yemek … | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt dışı günlük yemek harcırahı (75 Euro) TL cinsinden 4.163,48 TL'ye eşittir (1 Euro = 55,513 TRY). Bu, yur… |
| a12 | Yurt dışında 3 günlük bir iş seyahatinde toplam yemek harcı… | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | 3 günlük yurt dışında iş seyahatinizde günlük yemek harcırahı 75 Euro'dur ([1] kaynak). Toplam harcırahınız: … |
