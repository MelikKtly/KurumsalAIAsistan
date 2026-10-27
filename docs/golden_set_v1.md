# Golden Set v1 — Elle Değerlendirme

**Tarih:** 2026-10-27
**Yapılandırma:** LLM `qwen3:8b` · prompt `rag/v2` · groundedness hakemi **açık** · embedding `paraphrase-multilingual-MiniLM-L12-v2` · top_k 4
**Soru seti:** `data/eval/golden_set.yaml` (15 soru: 12 cevaplanabilir, 2 dokümanda yok, 1 konu dışı)
**Yeniden çalıştırmak için:** `uv run python -m scripts.run_golden --out logs/golden_sonuclar.json`

Bu sorular geliştirme sırasında **hiç kullanılmadı**; prompt ve hakem bunlara bakılarak ayarlanmadı. Bu yüzden sonuç, sistemin yeni sorulardaki gerçek başarısına daha yakın bir tahmindir. Golden set üzerinde ayar yapılmamalı; yalnızca ölçüm için kullanılmalı.

## Özet

| Ölçüt | Sonuç |
| --- | --- |
| **Elle değerlendirme: tam doğru** | **12/15 (%80)** |
| Kısmen doğru (bilgi doğru, biçim bozuk) | 1/15 (g10) |
| Yanlış (yanlış cevap türü) | 2/15 (g13, g14) |
| Uydurma bilgi içeren cevap | **0/15** |
| Cevaplanabilir sorularda bilgi doğru | **12/12** |
| Atıf doğru sayfaya | 11/12 (g07 yanlış numara) |
| Hakem: doğrulandı / uydurma şüphesi | 12 / 0 (elle kontrolle uyumlu, yanlış alarm yok) |
| Otomatik kontrol (must_contain + answer_type) | 13/15 |
| Ortalama süre (hakem dahil) | ~14.5 sn |

## Soru bazında

| id | Soru | Cevap (özet) | Not | Gerekçe |
| --- | --- | --- | --- | --- |
| g01 | Doğum günümde izinli olabilir miyim? | "Evet, 1 gün ek izin" [1] | ✅ | |
| g02 | Masrafları en geç ne zaman girmeliyim? | "30 gün içinde, fatura/fişle" [3] | ✅ | "Süreyi geçen ödenmez" kısmı yok, soru için gerekli değil |
| g03 | Yemek kartına günlük ne kadar? | "İş günü başına 450 TL" [2] | ✅ | |
| g04 | Sağlık sigortası aileyi kapsıyor mu? | "Evet, birinci derece aile üyeleri" [1] | ✅ | Küçük dil bilgisi hatası |
| g05 | Şüpheli e-postayı kime bildirmeli? | "guvenlik@ornekteknoloji.com" [4] | ✅ | Cevapta `**...**` Markdown işareti var; arayüz düz metin gösterdiği için yıldızlar görünür (kozmetik) |
| g06 | Yurt dışından kaç gün uzaktan çalışma? | "Yılda en fazla 30 gün" [1] | ✅ | "2 hafta önce onay" kısmı yok, soru için gerekli değil |
| g07 | Evlenirsem kaç gün izin? | "5 gün ücretli mazeret izni" [2] | ✅ | Bilgi doğru ama **atıf yanlış**: bilgi [1]'de, model [2] dedi |
| g08 | İK'ya nasıl ulaşırım? | "ik@… veya dahili 2400" [1] | ✅ | |
| g09 | Kullanılmayan izin devreder mi? | "En fazla 5 günü devreder" [1] | ✅ | |
| g10 | 20 yıldır buradayım, kaç gün izin? | Soruyu tekrar etti + "26 iş günü" [1] | ⚠️ | Çıkarım doğru (15 yıl üstü → 26), ama cevap **soruyu kelimesi kelimesine tekrarlayarak** başlıyor |
| g11 | Şirket ne zaman, nerede kuruldu? | "2015, İstanbul" [1] | ✅ | |
| g12 | İzin talebi kaç gün önceden? | "En az 5 iş günü, İK portalı" [1] | ✅ | |
| g13 | Şirketin yıllık cirosu? | "Bu konuda yardımcı olamıyorum; yalnızca şirket dokümanlarıyla…" | ❌ | Uydurmadı, ama **yanlış ret türü**: şirketle ilgili bir soru, "dokümanlarda yer almıyor" denmeliydi (`off_topic` yerine `not_found`) |
| g14 | Kreş yardımı var mı? | Aynı konu dışı cevabı | ❌ | g13 ile aynı: tipik bir İK yan hak sorusuna "şirketle ilgili değil" demek kullanıcıyı yanıltır |
| g15 | Bana kitap önerir misin? | Konu dışı cevabı | ✅ | |

## Bulgular

1. **Bilgi doğruluğu çok iyi:** Cevaplanabilir 12 sorunun 12'sinde doğru bilgi var ve hiçbir cevapta uydurma yok. Hakem de bununla uyumlu; hiç yanlış alarm vermedi.
2. **Yeni bir hata türü (geliştirme setinde görülmemişti):** Dokümanda olmayan *şirket* soruları ("ciro", "kreş yardımı") **konu dışı** olarak reddedildi. Geliştirme setindeki benzer 4 soruda (CEO, maaş zammı, araba, Ankara adresi) model doğru şekilde "dokümanlarda yer almıyor" demişti. Bu, geliştirme setinin genellemeyi tam ölçemediğini ve ayrı bir golden set tutmanın neden gerekli olduğunu gösteriyor.
   - Muhtemel neden: v2 promptundaki "şirketle ilgili değilse" kuralı, "dokümanda yok" kuralından **önce** geliyor. Model, bağlamda ilgili bilgi göremeyince ilk eşleşen kurala gidiyor olabilir.
3. **Biçim sorunları:** Soruyu tekrar etme (g10) ve Markdown kalın yazı işareti (g05). Bilgiyi bozmuyor ama kullanıcı deneyimini etkiliyor.
4. **Atıf numarası hatası** hâlâ ara sıra oluyor (g07). Hakem atıf numaralarını kontrol etmiyor (promptunda bilerek "yok say" deniyor), bu yüzden bu hatayı yakalamıyor.

## Öneriler (golden set dışında, geliştirme setiyle yapılmalı)

- **v3 prompt:** "Dokümanda yok" ve "konu dışı" kurallarının sırasını ve tanımını netleştir ("İK, yan haklar, maaş, şirket bilgisi gibi konular dokümanda yoksa bile *şirketle ilgilidir*"). Önce geliştirme setine (`questions.yaml`) ciro/kreş türü yeni sorular eklenmeli, v3 orada v2 ile karşılaştırılmalı, ardından golden set **bir kez** yeniden ölçülmeli.
- **Biçim:** Prompta "soruyu tekrar etme, Markdown kullanma" talimatı eklenebilir.
- Bu set Faz 4.6'daki otomatik eval scriptinin girdisi olacak (must_contain + expected_answer_type).
