# Prompt Versiyonları Karşılaştırması

**Tarih:** 2026-10-25  
**LLM:** `qwen3:8b` · **Embedding:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` · **top_k:** 4  
**Soru seti:** `data/eval/questions.yaml` (29 soru)  
**Yeniden üretmek için:** `uv run python -m scripts.eval_prompts --versions v1 v2 --out docs/prompt_karsilastirma.md`

Her soru için retrieval bir kez yapıldı; aynı chunk'lar her versiyona verildi.
Puanlama kural tabanlıdır (anahtar kelime, ret ifadesi, atıf geçerliliği) — anlamı tam ölçmez.

## Versiyonlar

- **v1:** Faz 1.6'daki sade prompt. Bağlama dayanma ve [n] atıfı talimatı var; selamlaşma / konu dışı mesajlar için kural yok.
- **v2:** Faz 1.10'daki kurallı prompt. Selamlaşma, konu dışı mesaj, şirket sorusu ve "dokümanda yok" durumları için ayrı kurallar ve sabit cevap kalıpları içerir.

## Özet

| Ölçüt | v1 | v2 |
| --- | --- | --- |
| **Toplam geçen** | **22/29 (%76)** | **28/29 (%97)** |
| Doğrudan bilgi | 8/9 (%89) | 8/9 (%89) |
| Çıkarım | 8/8 (%100) | 8/8 (%100) |
| Dokümanda yok | 4/4 (%100) | 4/4 (%100) |
| Selamlaşma | 0/4 (%0) | 4/4 (%100) |
| Konu dışı | 2/4 (%50) | 4/4 (%100) |
| Beklenen bilgi cevapta (cevaplanabilir) | 16/17 (%94) | 16/17 (%94) |
| Doğru chunk'a atıf (chunk getirildiyse) | 15/16 (%94) | 15/16 (%94) |
| Geçersiz atıf sayısı | 0 | 0 |
| Ortalama süre (ilk hariç) | 6.6 sn | 7.4 sn |

## Soru bazında

| id | Soru | Beklenen | Retrieval sırası | v1 | v2 |
| --- | --- | --- | --- | --- | --- |
| d01 | Standart çalışma saatleri nedir? | Hafta içi 09:00–18:00 | ❌ yok | ❌ *beklenen bilgi yok*<br>Standart çalışma saatleri 07:30 ile 10:00 arasında herhangi bir saatte başlayabilir. [2] | ❌ *beklenen bilgi yok*<br>Standart çalışma saatleri 07:30 ile 10:00 arasında herhangi bir saatte başlayabilirler [2]. |
| d02 | Fazla mesai ücreti nasıl hesaplanır? | Saatlik ücretin %50 fazlası, yönetici y… | 3 | ✅<br>Fazla mesai ücreti normal saatlik ücretin yüzde 50 fazlası olarak hesaplanır [3]. | ✅<br>Fazla mesai ücreti normal saatlik ücretin yüzde 50 fazlası olarak hesaplanır [3]. |
| d03 | Uzaktan çalışanlara internet desteği ne kadar? | Aylık 1.500 TL | 1 | ✅<br>Uzaktan çalışanlara her ay 1.500 TL internet ve elektrik desteği ödenir [1]. | ✅<br>Uzaktan çalışan personele her ay 1.500 TL internet ve elektrik desteği ödenir [1]. |
| d04 | Babalık izni kaç gün? | 10 gün | 1 | ✅<br>Babalık izni 10 gündür [1]. | ✅<br>Babalık izni 10 gündür [1]. |
| d05 | Yurt içinde konaklama için gecelik limit nedir? | 4.000 TL | 1 | ✅<br>Yurt içinde konaklama için gecelik üst limit 4.000 TL'dir [1]. | ✅<br>Yurt içinde konaklama için gecelik üst limit 4.000 TL'dir [3]. |
| d06 | Yıllık eğitim bütçem ne kadar? | 15.000 TL | 1 | ✅<br>Yıllık eğitim bütçeniz 15.000 TL'dir [1]. | ✅<br>Yıllık eğitim bütçeniz 15.000 TL'dir [1]. |
| d07 | Spor salonu için destek var mı? | Aylık 1.000 TL'ye kadar | 1 | ✅<br>Evet, spor salonu üyeliği için aylık 1.000 TL'ye kadar destek sağlanır [1]. | ✅<br>Evet, spor salonu üyeliği için aylık 1.000 TL'ye kadar destek sağlanır [1]. |
| d08 | Şifrem en az kaç karakter olmalı? | En az 12 karakter | 3 | ✅<br>Şifreniz en az 12 karakter olmalıdır [3]. | ✅<br>Şifreniz en az 12 karakter olmalıdır [3]. |
| d09 | Yurt dışında yemek harcırahı ne kadar? | 75 Euro | 1 | ✅<br>Yurt dışında yemek harcırahı 75 Euro'dur [1]. | ✅<br>Yurt dışında yemek harcırahı 75 Euro'dur [1]. |
| c01 | Mesaiye en geç saat kaçta başlayabilirim? | 10:00 | 4 | ✅<br>Mesaiye en geç 10:00'ta başlayabilirisiniz. [1] | ✅<br>Çalışanlar mesailerine 10:00 ile 16:00 arasındaki çekirdek saatlerde çevrimiçi olmak koşuluyla 07:30 ile 10:00 arasında herhangi bir saatte… |
| c02 | Kıdemim 3 yıl, kaç gün yıllık iznim var? | 14 iş günü | 1 | ✅<br>Kıdeminiz 3 yıl olduğuna göre yıllık izniniz 14 iş gündür. [1] | ✅<br>Kıdemim 3 yıl olduğuna göre yılda 14 iş günü ücretli yıllık izin hakkına sahipsiniz [1]. |
| c03 | Kıdemim 7 yıl, kaç gün yıllık iznim var? | 20 iş günü | 1 | ✅<br>Kıdeminiz 7 yıl olduğuna göre yıllık izniniz 20 iş gündür. [1] | ✅<br>Kıdemim 7 yıl olduğuna göre yıllık iznin 20 iş günüdür [1]. |
| c04 | 3 gün hasta olursam doktor raporu gerekir mi? | Evet, 2 günü aşan izinlerde zorunlu | 1 | ✅<br>Evet, 2 günü aşan hastalık izinleri için doktor raporu zorunludur [1]. | ✅<br>Evet, 2 günü aşan hastalık izinleri için doktor raporu zorunludur [1]. |
| c05 | 6.000 TL'lik bir harcama için onay almam gerekir mi? | Evet, departman direktöründen önceden | 1 | ✅<br>Evet, 6.000 TL'lik bir harcama için onay almam gerekir. 5.000 TL üzerindeki tüm harcamalar için önceden departman direktörünün onayı gerekl… | ✅<br>Evet, 5.000 TL üzerindeki tüm harcamalar için önceden departman direktörünün onayı gereklidir [1]. |
| c06 | 12.000 TL'lik bir sertifikayı şirket ödedi, bitirince hemen… | Hayır, en az 1 yıl çalışma taahhüdü var | 1 | ✅<br>Hayır, 12.000 TL'lik bir sertifika programına katılan çalışan, programın bitiminden sonra en az 1 yıl şirkette çalışmayı taahhüt etmektedir… | ✅<br>Hayır, 12.000 TL'lik bir sertifikayı şirket ödediyseniz, programın bitiminden itibaren en az 1 yıl şirkette çalışmanız gerekmektedir [1]. |
| c07 | Hangi günler ofiste olmam gerekiyor? | Salı ve Perşembe | 2 | ✅<br>Salı ve Perşembe günleri tüm ekipler için ofis günü olarak belirlenmiştir. [2] | ✅<br>Salı ve Perşembe günleri tüm ekipler için ofis günü olarak belirlenmiştir [2]. |
| c08 | Evden haftada kaç gün çalışabilirim? | En fazla 3 gün | 1 | ✅<br>Haftada en fazla 3 gün uzaktan çalışabilirsiniz. [1] | ✅<br>Haftada en fazla 3 gün uzaktan çalışabilirsiniz. Salı ve Perşembe günleri tüm ekipler için ofis günü olarak belirlenmiştir [1]. |
| y01 | Şirketin CEO'su kim? | Dokümanda yok | — | ✅<br>Bağlamda CEO'nun kim olduğu belirtilmemiştir. | ✅<br>Bu bilgi dokümanlarda yer almıyor. |
| y02 | Maaş zamları hangi ay yapılıyor? | Dokümanda yok | — | ✅<br>Bağlamda maaş zamlarıyla ilgili bilgi yer almamıştır. | ✅<br>Bu bilgi dokümanlarda yer almıyor. |
| y03 | Şirket araba veriyor mu? | Dokümanda yok | — | ✅<br>Bağlamda şirketin araba verip vermediği hakkında bilgi bulunmamaktadır. | ✅<br>Bu bilgi dokümanlarda yer almıyor. |
| y04 | Ankara ofisinin adresi nedir? | Ankara'da şube var, adres dokümanda yok | — | ✅<br>Bağlamda Ankara ofisinin adresi belirtilmemiştir. | ✅<br>Bu bilgi dokümanlarda yer almıyor. |
| s01 | Nasılsın? | Kısa karşılık + yönlendirme | — | ❌ *gereksiz atıf*<br>İyiyim, size nasıl yardımcı olabilirim? [1] | ✅<br>İyiyim, size nasıl yardımcı olabilirim? |
| s02 | Merhaba | Kısa karşılık + yönlendirme | — | ❌ *gereksiz atıf*<br>Merhaba! Size nasıl yardımcı olabilirim? [1] | ✅<br>Merhaba, şirket dokümanlarıyla ilgili sorularınızı cevaplayabilirim. |
| s03 | Teşekkürler | Kısa karşılık | — | ❌ *gereksiz atıf*<br>Çalışanların sorularına yardımcı olmaktan memnuniyet duyarım. Dilerseniz sorunuzu sorabilirsiniz. [1] | ✅<br>Çalışan el kitabında yer alan bilgilerle ilgili sorulara yardımcı olmaktan memnuniyet duyarım. |
| s04 | Günaydın, iyi çalışmalar | Kısa karşılık | — | ❌ *gereksiz atıf*<br>Günaydın! İyi çalışmalar dilerim. [1] | ✅<br>Günaydın! İyi çalışmalar dilerim. Şirket dokümanlarıyla ilgili sorulara yardımcı olabilirim. |
| a01 | Bana bir fıkra anlat | Ret | — | ❌ *ret ama atıf var*<br>Üzgünüm, bir fıkra anlatamam. Çünkü elimdeki bilgiler sadece bir şirketin çalışanlarına yönelik kurumsal politalarını içeriyor ve fıkralarl… | ✅<br>Bu konuda yardımcı olamıyorum; yalnızca şirket dokümanlarıyla ilgili soruları cevaplayabiliyorum. |
| a02 | Python'da liste nasıl sıralanır? | Ret | — | ✅<br>Bu soruyla ilgili bilgi bağlamda yer almamaktadır. | ✅<br>Bu konuda yardımcı olamıyorum; yalnızca şirket dokümanlarıyla ilgili soruları cevaplayabiliyorum. |
| a03 | Bugün hava nasıl? | Ret | — | ✅<br>Bu soru bağlamda yer almamaktadır. | ✅<br>Bu konuda yardımcı olamıyorum; yalnızca şirket dokümanlarıyla ilgili soruları cevaplayabiliyorum. |
| a04 | Türkiye'nin başkenti neresi? | Ret | — | ❌ *ret etmedi*<br>Türkiye'nin başkenti Ankara'dır [1]. | ✅<br>Bu konuda yardımcı olamıyorum; yalnızca şirket dokümanlarıyla ilgili soruları cevaplayabiliyorum. |
