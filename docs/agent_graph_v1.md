# Agent Değerlendirmesi: `graph`

**Tarih:** 2026-10-27 · **Model:** `qwen3:8b` · **Prompt:** `agent/v1` · **Görev seti:** `data/eval/agent_tasks.yaml` (12 görev)  
**Yeniden üretmek için:** `uv run python -m scripts.eval_agent --agent graph --prompt v1 --out docs/agent_graph_v1.md`

| Ölçüt | Sonuç |
| --- | --- |
| **Görev başarısı** (doğru araçlar + beklenen bilgi) | **11/12** |
| Doğru araç seçimi | 11/12 |
| Beklenen bilgi cevapta | 12/12 |
| Ortalama LLM çağrısı | 2.1 |
| Ortalama süre | 63.7 sn |
| Ortalama token | 3510 |

| id | Soru | Beklenen araçlar | Çağrılan araçlar | Sonuç | Cevap |
| --- | --- | --- | --- | --- | --- |
| a01 | Babalık izni kaç gün? | search_documents | search_documents | ✅ | Babalık izni 10 gündür. [1] kaynak numarasına göre, evlilik durumunda 5 gün, babalık izni olarak 10 gün ve bi… |
| a02 | Yıllık eğitim bütçem ne kadar? | search_documents | search_documents | ✅ | Yıllık eğitim bütçeniz **15.000 TL**'dir. Bu bütçe kurs, sertifika, konferans ve kitap harcamaları için kulla… |
| a03 | Şifrem en az kaç karakter olmalı? | search_documents | search_documents | ✅ | Şifreler en az **12 karakter** olmalıdır. Bu bilgi [2] numaralı kaynakta yer almaktadır. |
| a04 | 1 Euro bugün kaç TL? | get_exchange_rate | get_exchange_rate | ✅ | 1 Euro (EUR) bugün 55,513 Türk Lirası (TRY) ediyor. (Tarih: 2026-10-27, Kaynak: Avrupa Merkez Bankası) |
| a05 | 100 Amerikan doları kaç Euro eder? | get_exchange_rate | get_exchange_rate | ✅ | 100 Amerikan Doları (USD) şu anki kuru (2026-10-27) 89.69 Euro (EUR) ediyor. [1] Kaynak: Avrupa Merkez Bankası |
| a06 | Yurt dışı günlük yemek harcırahım kaç TL eder? | search_documents, get_exchange_rate | search_documents | ❌ araç | Yurt dışı günlük yemek harcırahı **75 Euro**'dur ([1] ve [4] kaynakları). Bu tutarın Türk Lirası (TL) karşılı… |
| a07 | Yurt içi gecelik konaklama limiti kaç Euro'ya denk geliyor? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt içi gecelik konaklama üst limiti **4.000 TL**'dir ([1] kaynak). **Dönüştürülmüş tutar:** 4.000 TL × 0.01… |
| a08 | Yıllık eğitim bütçem kaç dolar eder? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yıllık eğitim bütçeniz **15.000 TL**'dir. Bu tutarın dolar cinsinden karşılığı şu şekildedir: **15.000 TL × 0… |
| a09 | Merhaba, nasılsın? | — | — | ✅ | Merhaba! Yardımcı olmaya hazırım, sorularınızı cevaplayabilirim. Nasıl yardımcı olabilirim? 😊 |
| a10 | Teşekkürler, çok yardımcı oldun. | — | — | ✅ | Çok memnun oldum! Size nasıl yardımcı olabilirim? |
| a11 | Yurt dışı günlük yemek harcırahı ile yurt içi günlük yemek … | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt dışı günlük yemek harcırahı (75 EUR) TL cinsinden hesaplanırsa: 75 EUR × 55.513 TRY/EUR = **4.163,48 TRY… |
| a12 | Yurt dışında 3 günlük bir iş seyahatinde toplam yemek harcı… | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt dışında 3 günlük iş seyahatinizde günlük yemek harcırahı 75 Euro'dur ([1] kaynak). Toplam harcırahınız: … |
