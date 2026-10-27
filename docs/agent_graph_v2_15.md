# Agent Değerlendirmesi: `graph`

**Tarih:** 2026-10-27 · **Model:** `qwen3:8b` · **Prompt:** `agent/v2` · **Görev seti:** `data/eval/agent_tasks.yaml` (15 görev)  
**Yeniden üretmek için:** `uv run python -m scripts.eval_agent --agent graph --prompt v2 --out docs/agent_graph_v2_15.md`

| Ölçüt | Sonuç |
| --- | --- |
| **Görev başarısı** (doğru araçlar + beklenen bilgi) | **12/15** |
| Doğru araç seçimi | 13/15 |
| Beklenen bilgi cevapta | 13/15 |
| Ortalama LLM çağrısı | 2.1 |
| Ortalama süre | 58.7 sn |
| Ortalama token | 4361 |

| id | Soru | Beklenen araçlar | Çağrılan araçlar | Sonuç | Cevap |
| --- | --- | --- | --- | --- | --- |
| a01 | Babalık izni kaç gün? | search_documents | search_documents | ✅ | Babalık izni 10 gündür. [1] |
| a02 | Yıllık eğitim bütçem ne kadar? | search_documents | search_documents | ✅ | Yıllık eğitim bütçeniz 15.000 TL'dir. Bu tutar, kurs, sertifika, konferans ve kitap harcamaları için kullanab… |
| a03 | Şifrem en az kaç karakter olmalı? | search_documents | search_documents | ✅ | Şifreler en az 12 karakter olmalıdır ve her 90 günde bir değiştirilmelidir. [3] |
| a04 | 1 Euro bugün kaç TL? | get_exchange_rate | get_exchange_rate | ✅ | 1 Euro bugün 55.513 TL'dir (tarih: 2026-10-27, kaynak: Avrupa Merkez Bankası). |
| a05 | 100 Amerikan doları kaç Euro eder? | get_exchange_rate | get_exchange_rate | ✅ | 100 USD = 89,69 EUR (kuru: 0,89686, tarih: 2026-10-27). |
| a06 | Yurt dışı günlük yemek harcırahım kaç TL eder? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt dışı günlük yemek harcırahı **75 Euro**'dur. Bu tutar, **55.513 TRY** (Avrupa Merkez Bankası, 2026-10-27… |
| a07 | Yurt içi gecelik konaklama limiti kaç Euro'ya denk geliyor? | search_documents, get_exchange_rate | search_documents | ❌ araç | Yurt içi gecelik konaklama üst limiti **4.000 TL**'dir ([1], [3]). Bu tutarın Euro cinsinden karşılığını bulm… |
| a08 | Yıllık eğitim bütçem kaç dolar eder? | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yıllık eğitim bütçeniz 15.000 TL'dir ([1] kaynak). Bu tutarın dolar cinsinden karşılığı, 2026-10-27 tarihli A… |
| a09 | Merhaba, nasılsın? | — | — | ✅ | Merhaba! Ben Sen Örnek Teknoloji A.Ş.'nin çalışanlarına yardım eden asistanım. Ne yapabilirim? |
| a10 | Teşekkürler, çok yardımcı oldun. | — | — | ✅ | Çok memnun oldum! Her zaman yardımcı olmaya hazırım. Dilerseniz sorularınızı veya ihtiyaçlarınızı bildirin. 😊 |
| a11 | Yurt dışı günlük yemek harcırahı ile yurt içi günlük yemek … | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ✅ | Yurt dışı günlük yemek harcırahı 75 EUR'dur ve bu tutar 55.513 TRY/USD kuruyla hesaplanırsa: **75 EUR × 55.51… |
| a12 | Yurt dışında 3 günlük bir iş seyahatinde toplam yemek harcı… | search_documents, get_exchange_rate | get_exchange_rate, search_documents | ❌ içerik | Yurt dışı 3 günlük iş seyahatinizde günlük yemek harcırahı 75 Euro'dur ([1] kaynak). 2026-10-27 tarihindeki E… |
| a13 | Ayşe Yılmaz'ın yıllık izin hakkı kaç gün? | query_employees, search_documents | query_employees | ❌ araç | Ayşe Yılmaz'ın bu yıl kullandığı yıllık izin sayısı 8 gündür ([1]). Ancak "yıllık izin hakkı" sorusu genellik… |
| a14 | Can Öztürk bu yıl kaç gün daha yıllık izin kullanabilir? | query_employees, search_documents | query_employees, search_documents | ✅ | Can Öztürk'ün bu yıl kullanabileceği yıllık izin günleri şu şekilde hesaplanır: 1. **Toplam İzin Hakkı**: - 5… |
| a15 | İzmir ofisinde kaç çalışan var? | query_employees | query_employees | ✅ | İzmir ofisinde 2 çalışan vardır. Daha fazla bilgi gerekli mi? |
