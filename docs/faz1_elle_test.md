# Faz 1 — Elle Test Sonuçları

**Tarih:** 23 Ekim 2026
**Doküman:** `data/samples/ornek_ik_el_kitabi.pdf` (3 sayfa → 5 chunk)
**Ayarlar:** LLM `qwen3:1.7b` (Ollama, temperature=0), embedding `paraphrase-multilingual-MiniLM-L12-v2`, chunk 1000/150, top_k=4
**Yeniden çalıştırmak için:** O zamanki `scripts/manual_test.py` Faz 2.2'de kaldırıldı; sorular `data/eval/questions.yaml`'a taşındı → `uv run python -m scripts.eval_prompts --versions v1`

## Özet

| Ölçüt | Sonuç |
| --- | --- |
| Cevap içeriği tamamen doğru | **12 / 18** (2 kısmen, 4 yanlış) |
| Doğru chunk ilk 4'te (retrieval recall@4) | **13 / 14** |
| Doğru chunk 1. sırada | 9 / 14 |
| Atıf numarası doğru | 9 / 14 |
| Dokümanda olmayan soruda uydurmama | **2 / 4** |
| Süre | İlk soru ~7.7 sn (model ısınması), sonrakiler 0.4–2.2 sn |

| Kategori | Doğru | Kısmen | Yanlış |
| --- | --- | --- | --- |
| Doğrudan bilgi (8) | 5 | 2 | 1 |
| Çıkarım (6) | 5 | 0 | 1 |
| Dokümanda yok / kısmen (4) | 2 | 0 | 2 |

## Soru bazında

Chunk sıraları: 0 = Giriş + Çalışma Saatleri, 1 = Çalışma Saatleri (devam) + Uzaktan Çalışma, 2 = İzinler, 3 = Masraf, 4 = Eğitim + Yan Haklar + Bilgi Güvenliği.

| # | Kategori | Soru | Beklenen | Model cevabı (özet) | İçerik | Doğru chunk sırası | Atıf |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | doğrudan | Standart çalışma saatleri nedir? | 09:00–18:00 | "9 saat, 2 saat dinlenme…" (uydurma, araya Çince karakter karıştı) | ❌ | yok | ❌ `[K1]` |
| 2 | doğrudan | Fazla mesai ücreti nasıl hesaplanır? | %50 fazlası | "yüzde 50'ine göre" (anlam kaymış: %50'si ≠ %50 fazlası) | ⚠️ | 3 | ✅ |
| 3 | doğrudan | İnternet desteği ne kadar? | Aylık 1.500 TL | Aylık 1.500 TL, ayın son iş günü | ✅ | 1 | ❌ |
| 4 | doğrudan | Babalık izni kaç gün? | 10 gün | 10 gün | ✅ | 1 | ✅ |
| 5 | doğrudan | Yurt içi konaklama gecelik limiti? | 4.000 TL | 4.000 TL | ✅ | 1 | ✅ |
| 6 | doğrudan | Yıllık eğitim bütçem? | 15.000 TL | 15.000 TL | ✅ | 1 | ✅ |
| 7 | doğrudan | Spor salonu desteği var mı? | Aylık 1.000 TL'ye kadar | "Var" + alakasız sertifika cümlesi, tutar yok | ⚠️ | 1 | ✅ |
| 8 | doğrudan | Şifre en az kaç karakter? | 12 | 12 karakter | ✅ | 3 | ❌ |
| 9 | çıkarım | Mesaiye en geç kaçta başlayabilirim? | 10:00 | 10:00 | ✅ | 4 | ✅ |
| 10 | çıkarım | Kıdemim 3 yıl, kaç gün izin? | 14 iş günü | 14 iş günü | ✅ | 1 | ✅ |
| 11 | çıkarım | 3 gün hastaysam rapor gerekir mi? | Evet (2 günü aşan) | Evet, 2 günü aşanlarda zorunlu | ✅ | 1 | ✅ |
| 12 | çıkarım | 6.000 TL harcama için onay? | Evet, direktör | Evet, 5.000 TL üstü direktör onayı | ✅ | 1 | ❌ |
| 13 | çıkarım | 12.000 TL sertifika sonrası hemen ayrılabilir miyim? | Hayır, 1 yıl taahhüt | "Hemen ayrılabilirsiniz… 1 yıl taahhüt edebilirsiniz" (çelişkili) | ❌ | 1 | ✅ |
| 14 | çıkarım | Hangi günler ofisteyim? | Salı, Perşembe | Salı ve Perşembe | ✅ | 2 | ❌ |
| 15 | yok | Şirketin CEO'su kim? | Yok | "Belirtilmemiştir" | ✅ | — | — |
| 16 | yok | Maaş zamları hangi ay? | Yok | "Belirtilmeden önceki ayda yapılmıştır" (anlamsız uydurma) | ❌ | — | — |
| 17 | yok | Şirket araba veriyor mu? | Yok | "Şirket araba vermiyor" (dokümanda olmayan bir iddia) | ❌ | — | — |
| 18 | kısmen | Ankara ofisinin adresi? | Şube var, adres yok | "Adres belirtilmemiştir" | ✅ | — | — |

## Bulgular

1. **Retrieval büyük ölçüde iyi:** 14 sorudan 13'ünde doğru chunk LLM'e ulaştı. Tek kaçırma (#1) en ciddi hataya yol açtı: doğru bilgi gelmeyince model uydurdu.
2. **Asıl zayıf halka küçük LLM:**
   - Dokümanda cevabı olmayan sorularda yarı yarıya uyduruyor (#16, #17); promptta "tahmin yürütme" talimatı olmasına rağmen.
   - Çıkarım gerektiren olumsuz cevaplarda çelişkiye düşüyor (#13).
   - İlgisiz cümle ekliyor (#7), anlamı kaydırıyor (#2) ve bazen başka dilden karakter karıştırıyor (#1).
   - Atıf numaralarında 14'te 5 hata yaptı (`[K1]` gibi uydurma format veya yanlış numara).
3. **Uzaklık eşiği "bilmiyorum" için tek başına yetmez:** Doğru cevabı olan sorularda bile en iyi uzaklık 0.83–0.84'e çıkabiliyor (#7, #8). Cevabı olmayan "araba" sorusunda da 0.83. Eşik yerine Faz 2'deki groundedness kontrolü gerekli.
4. **Büyük chunk sorunu doğrulandı:** Üç konuyu birden içeren chunk 4, şifre sorusunda 3. sıraya düştü. "Standart çalışma saatleri" sorusunda ise en yakın chunk İzinler bölümü (0.31) geldi.

## Faz 2 için öneriler

- Bu 18 soru ve beklenen cevaplar, Faz 2.8'deki **golden set**'in başlangıcı olarak kullanılabilir.
- Önce **daha büyük bir model** (ör. `qwen3:4b` / `qwen3:8b`) ile aynı seti çalıştırıp karşılaştır. Bulguların çoğu modelin küçüklüğünden kaynaklanıyor.
- Prompt versiyonları (2.2), açık "bilmiyorum" fallback'i (2.3) ve groundedness kontrolü (2.4), #13, #16 ve #17 tipi hataları hedeflemeli.
- Retrieval için daha küçük ya da başlık bazlı chunk ve reranking denenebilir.

---

## Model ve prompt karşılaştırması

Aynı 18 soru ile 8 konu dışı mesaj (selamlaşma, teşekkür, fıkra, hava, programlama, genel kültür) üç yapılandırmada çalıştırıldı. Retrieval üçünde de aynı; fark sadece LLM'de ve promptta.

- **Mevcut prompt:** "Bağlama dayan, `[n]` ile atıf yap, bağlamda yoksa söyle."
- **Kurallı prompt:** Selamlaşma, konu dışı, şirket sorusu ve "dokümanda yok" durumları için ayrı kurallar ve sabit cevap kalıpları.

| Ölçüt | 1.7B + mevcut | 8B + mevcut | 8B + kurallı |
| --- | --- | --- | --- |
| Cevap içeriği doğru (18) | 12 (2 kısmen) | **17** | 16 (1 kısmen) |
| Atıf doğru (doğru cevaplarda) | 9 / 14 | **13 / 13** | 12 / 13 |
| Dokümanda yok → uydurmadı (4) | 2 | **4** | **4** (sabit kalıpla) |
| Konu dışı mesajı doğru ele aldı (8) | 0–1 | 5 | **8** |
| Ortalama süre (ilk soru hariç) | **1.6 sn** | 6.2 sn | 6.6 sn |
| İlk soru (model yükleme) | 7.7 sn | 18.9 sn | 16.0 sn |

### Notlar

- **1.7B ile kurallı prompt denendi ve geri alındı.** Konu dışı mesajları reddetmeye başladı, ama "Kıdemim 7 yıl" sorusunda doğru cevap olan 20 gün yerine 14 gün dedi. Küçük model uzun talimatlarla çıkarım yeteneğini kaybediyor.
- **1.7B ile LLM tabanlı niyet sınıflandırma:** 26 mesajın 10'u doğru. "Babalık izni" gibi meşru soruları "alakasız" saydı, kullanılamaz.
- **Embedding tabanlı yönlendirme (LLM'siz):** 30 mesajın 28'i doğru, ama örnek cümleler test setini görerek yazıldığı için iyimser bir ölçüm. 8B ile kurallı prompt bu problemi zaten çözdüğü için şimdilik gerek yok; düşük gecikme ya da maliyet gerektiğinde tekrar değerlendirilebilir.
- **8B + mevcut prompt** selamlaşmalara doğal karşılık veriyor ama gereksiz `[1]` ekliyor. Ayrıca "Türkiye'nin başkenti?" sorusunu kendi bilgisinden cevaplayıp bir de kaynak gösteriyor. Bu, olmayan bir kaynağa dayanıyormuş gibi yapmak demek.
- **#1 "Standart çalışma saatleri"** her yapılandırmada yanlış, çünkü sorun retrieval'da: doğru chunk ilk 4'e girmiyor. 8B uydurmuyor, gelen bağlamdaki 07:30–10:00 bilgisini veriyor. Çözüm LLM tarafında değil, chunking ya da reranking tarafında.
- **Kaynak kullanımı:** 8B, M4 / 16 GB RAM'de sorunsuz çalışıyor; diskte 5.2 GB. Hız 1.7B'ye göre ~4 kat yavaş.

### Sonuç

**8B + kurallı prompt** en dengeli seçenek. Doğruluk ve dürüstlük belirgin şekilde arttı, konu dışı mesajların hepsi doğru ele alındı. Bedeli soru başına ~5 saniyelik ek gecikme.
