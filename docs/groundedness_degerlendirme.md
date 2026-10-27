# Groundedness Hakemi Değerlendirmesi

**Tarih:** 2026-10-27  
**Hakem modeli:** `qwen3:8b` · **Prompt:** `groundedness/v1`  
**Vaka seti:** `data/eval/groundedness.yaml` (22 vaka: 10 bağlama dayalı, 12 uydurma)  
**Yeniden üretmek için:** `uv run python -m scripts.eval_groundedness --out docs/groundedness_degerlendirme.md`

## Özet

| Ölçüt | Sonuç |
| --- | --- |
| **Doğruluk** | **22/22** |
| Uydurmayı yakalama (recall) | 12/12 |
| Yanlış alarm (doğru cevaba "uydurma") | 0/10 |
| Geçersiz karar (şemaya uymayan çıktı) | 0 |
| Ortalama hakem süresi (ilk hariç) | 5.8 sn |

## Vaka bazında

| id | Not | Cevap | Beklenen | Hakem | Hakemin desteksiz bulduğu / gerekçe |
| --- | --- | --- | --- | --- | --- |
| g01 | Doğrudan alıntı | Yurt dışında yemek harcırahı 75 Euro'dur [1]. | dayanıyor | ✅ dayanıyor | doğru |
| g02 | Kuralın soruya uygulanması (çıkarım) | Kıdeminiz 7 yıl olduğu için yıllık izniniz 20 iş günüdür [1]. | dayanıyor | ✅ dayanıyor | doğru |
| g03 | Çıkarım + olumsuz cevap | Hayır. Bedeli 10.000 TL'yi aşan sertifika programlarında, program bitiminden itibaren en … | dayanıyor | ✅ dayanıyor | doğru |
| g04 | Doğrudan | Salı ve Perşembe günleri ofiste olmanız gerekir [2]. | dayanıyor | ✅ dayanıyor | doğru |
| g05 | Birden fazla doğru iddia | Uzaktan çalışanlara her ay 1.500 TL internet ve elektrik desteği ödenir; bu tutar ayın so… | dayanıyor | ✅ dayanıyor | doğru |
| g06 | Çıkarım | Evet, 5.000 TL üzerindeki harcamalar için önceden departman direktörünün onayı gerekir [1… | dayanıyor | ✅ dayanıyor | doğru |
| g07 | Soruyu tam cevaplamıyor ama söylediği her şey bağ… | Çalışanlar mesailerine 07:30 ile 10:00 arasında herhangi bir saatte başlayabilir [2]. | dayanıyor | ✅ dayanıyor | doğru |
| g08 | Çıkarım | Evet, 2 günü aşan hastalık izinlerinde doktor raporu zorunludur [1]. | dayanıyor | ✅ dayanıyor | doğru |
| g09 | Doğrudan | Evet, spor salonu üyeliği için aylık 1.000 TL'ye kadar destek sağlanır [1]. | dayanıyor | ✅ dayanıyor | doğru |
| g10 | Farklı kelimelerle ifade (parafraz) | 3 yıllık kıdemle yılda 14 iş günü ücretli yıllık izin hakkınız bulunuyor [1]. | dayanıyor | ✅ dayanıyor | doğru |
| u01 | Yanlış sayı | Yurt dışında yemek harcırahı 100 Euro'dur [1]. | uydurma | ✅ uydurma | Yurt dışında yemek harcırahı 100 Euro'dur |
| u02 | Yanlış çıkarım (yanlış kıdem aralığı) | Kıdeminiz 7 yıl olduğu için yıllık izniniz 26 iş günüdür [1]. | uydurma | ✅ uydurma | Kıdeminiz 7 yıl olduğu için yıllık izniniz 26 iş günüdür |
| u03 | Faz 1'de 1.7B'nin gerçek cevabı — bağlamla çelişki | Şirket tarafından ödenen sertifikayı bitirince hemen ayrılabilirsiniz. Bu durumda sertifi… | uydurma | ✅ uydurma | Şirket tarafından ödenen sertifikayı bitirince hemen ayrılabilirsiniz. |
| u04 | Faz 1'de 1.7B'nin gerçek uydurması | Standart çalışma saatleri günde 9 saattir; çalışanlar 9 saat çalışma ve 2 saat dinlenme ş… | uydurma | ✅ uydurma | Standart çalışma saatleri günde 9 saattir; çalışanlar 9 saat çalışma ve 2 saat dinlenme şeklinde ça… |
| u05 | Gerçekte doğru, ama retrieval bu chunk'ı getirmiy… | Standart çalışma saatleri hafta içi 09:00 ile 18:00 arasındadır [1]. | uydurma | ✅ uydurma | Standart çalışma saatleri hafta içi 09:00 ile 18:00 arasındadır [1]. |
| u06 | Abartılmış / uydurma kapsam | Evet, şirket spor salonu üyeliğinin tamamını karşılar [1]. | uydurma | ✅ uydurma | şirket spor salonu üyeliğinin tamamını karşılar |
| u07 | Faz 2.2'de v1'in gerçek cevabı — genel kültürden … | Türkiye'nin başkenti Ankara'dır [1]. | uydurma | ✅ uydurma | Türkiye'nin başkenti Ankara'dır [1] |
| u08 | Doğru iddiaya eklenmiş uydurma iddia | Yurt dışında yemek harcırahı 75 Euro'dur; ayrıca yurt dışı konaklama için gecelik 200 Eur… | uydurma | ✅ uydurma | yurt dışı konaklama için gecelik 200 Euro üst limit vardır |
| u09 | Tamamen uydurma | Şirket, kıdemi 5 yılı geçen çalışanlara şirket aracı tahsis eder [1]. | uydurma | ✅ uydurma | Şirket, kıdemi 5 yılı geçen çalışanlara şirket aracı tahsis eder [1] |
| u10 | Doğru iddiaya eklenmiş uydurma iddia | Uzaktan çalışanlara her ay 1.500 TL internet desteği ödenir ve şirket ayrıca bir dizüstü … | uydurma | ✅ uydurma | şirket ayrıca bir dizüstü bilgisayar verir |
| u11 | Yanlış sayı | Haftada en fazla 4 gün evden çalışabilirsiniz [1]. | uydurma | ✅ uydurma | Haftada en fazla 4 gün evden çalışabilirsiniz |
| u12 | İnce anlam kayması (%50 fazlası ≠ %50'si) — Faz 1… | Fazla mesai ücreti, normal saatlik ücretin yüzde 50'si olarak hesaplanır [1]. | uydurma | ✅ uydurma | Fazla mesai ücreti, normal saatlik ücretin yüzde 50'si olarak hesaplanır [1] |

## Tasarım iterasyonları

Hakem üç aşamada geliştirildi; her aşama bu vaka setiyle ölçüldü.

| # | Hakem tasarımı | Doğruluk | Uydurma yakalama | Yanlış alarm | Hakem süresi |
| --- | --- | --- | --- | --- | --- |
| 1 | Şema: `grounded` → `unsupported_claims` → `reason` (önce karar) | 16/22 | 6/12 | 0/10 | 10–36 sn |
| 2 | Şema: `claims_check` → `unsupported_claims` → `grounded` (önce düşün) | 18/22 | 8/12 | 0/10 | ~6 sn |
| 3 | Model yalnızca iddiaları listeler; **karar kodda**: `grounded = not unsupported_claims` | **22/22** | **12/12** | **0/10** | ~5 sn |

**1 → 2:** LLM JSON alanlarını şemadaki sırayla üretir. `grounded` ilk alanken model kararı düşünmeden veriyor, ardından gerekçesinde çelişkiyi bulsa bile ("…'en fazla 3 gün' ile çelişmektedir… desteksizdir") kararı `true` olarak kalıyordu. Uzun ve kendi kararını savunmaya çalışan gerekçeler süreyi de uzatıyordu.

**2 → 3:** Kalan 4 hatada model desteksiz iddiayı listeye doğru yazmış (örn. `["şirket ayrıca bir dizüstü bilgisayar verir"]`), ama yine de `grounded: true` demişti. Karar alanı kaldırıldı; karar listeden deterministik olarak türetiliyor. İlke: LLM'e anlama/karşılaştırma işini, basit mantığı koda bırak.

## Sınırlar

- **Küçük ve kurgusal set:** 22 vaka, vakaları yazan kişi hakemin tasarımını da biliyor. Gerçek kullanımda doğruluk daha düşük olabilir. Faz 2.8'deki golden set ile genişletilmeli.
- **Hakem, cevabı üreten modelle aynı** (`qwen3:8b`). Aynı modelin kendi hatalarını görme konusunda kör noktaları olabilir; ileride farklı/daha güçlü bir hakem modeli (örn. Claude) denenebilir.
- **Gecikme:** Açıkken her kaynaklı cevaba ~5 sn eklenir.
