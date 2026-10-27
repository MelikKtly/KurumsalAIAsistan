# Agent Değerlendirmesi: `graph`

**Tarih:** 2026-10-27 · **Model:** `qwen3:8b` · **Görev seti:** `data/eval/agent_tasks.yaml` (10 görev)  
**Yeniden üretmek için:** `uv run python -m scripts.eval_agent --agent graph --out docs/agent_graph.md`

| Ölçüt | Sonuç |
| --- | --- |
| **Görev başarısı** (doğru araçlar + beklenen bilgi) | **9/10** |
| Doğru araç seçimi | 9/10 |
| Beklenen bilgi cevapta | 10/10 |
| Ortalama LLM çağrısı | 2.0 |
| Ortalama süre | 49.7 sn |
| Ortalama token | 3019 |

| id | Soru | Beklenen araçlar | Çağrılan araçlar | Sonuç | Cevap |
| --- | --- | --- | --- | --- | --- |
| a01 | Babalık izni kaç gün? | search_documents | search_documents | ✅ | Babalık izni 10 gündür. [1] kaynak numarasına göre, evlilik durumunda 5 gün, babalık izni olarak 10 gün ve bi… |
| a02 | Yıllık eğitim bütçem ne kadar? | search_documents | search_documents | ✅ | Yıllık eğitim bütçeniz **15.000 TL**'dir. Bu bütçe kurs, sertifika, konferans ve kitap harcamaları için kulla… |
| a03 | Şifrem en az kaç karakter olmalı? | search_documents | search_documents | ✅ | Şifreler en az **12 karakter** olmalıdır. Bu bilgi [2] numaralı kaynakta yer almaktadır. |
| a04 | 1 Euro bugün kaç TL? | get_exchange_rate | get_exchange_rate | ✅ | 1 Euro bugün 55,6746 TL'dir (tarih: 2026-10-26, kaynak: Avrupa Merkez Bankası). |
| a05 | 100 Amerikan doları kaç Euro eder? | get_exchange_rate | get_exchange_rate | ✅ | 100 Amerikan Doları (USD) şu anki döviz kuruyla 89.38 Euro (EUR) eder. Kur: 1 USD = 0.89381 EUR (tarih: 2026-… |
| a06 | Yurt dışı günlük yemek harcırahım kaç TL eder? | search_documents, get_exchange_rate | search_documents | ❌ araç | Yurt dışı günlük yemek harcırahı **75 Euro**'dur ([1] ve [4] kaynakları). Bu tutarın Türk Lirası (TL) karşılı… |
| a07 | Yurt içi gecelik konaklama limiti kaç Euro'ya denk geliyor? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt içi gecelik konaklama üst limiti **4.000 TL**'dir ([1] kaynak). **Dönüştürülmüş tutar:** 4.000 TL × 0.01… |
| a08 | Yıllık eğitim bütçem kaç dolar eder? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yıllık eğitim bütçeniz **15.000 TL**'dir. Bu tutarın dolar cinsinden karşılığı şu şekildedir: **15.000 TL × 0… |
| a09 | Merhaba, nasılsın? | — | — | ✅ | Merhaba! Yardımcı olmaya hazırım, sorularınızı cevaplayabilirim. Nasıl yardımcı olabilirim? 😊 |
| a10 | Teşekkürler, çok yardımcı oldun. | — | — | ✅ | Çok memnun oldum! Size nasıl yardımcı olabilirim? |
