"""Test için kurgusal bir şirket İK el kitabı PDF'i üretir.

İçerik bilerek somut ve doğrulanabilir bilgiler içerir (gün sayıları, tutarlar),
böylece RAG cevaplarının doğruluğu elle kontrol edilebilir.

Kullanım:
    uv run python scripts/create_sample_pdf.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUTPUT = Path("data/samples/ornek_ik_el_kitabi.pdf")

# Türkçe karakterler için TTF font gerekiyor (macOS)
FONT_DIR = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("Arial", FONT_DIR / "Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", FONT_DIR / "Arial Bold.ttf"))

SECTIONS = [
    (
        "1. Giriş",
        [
            "Bu el kitabı, Örnek Teknoloji A.Ş. çalışanlarının haklarını, sorumluluklarını "
            "ve şirket içi süreçleri açıklamak amacıyla İnsan Kaynakları Departmanı tarafından "
            "hazırlanmıştır. El kitabının bu sürümü 1 Ocak 2026 tarihinden itibaren geçerlidir.",
            "Örnek Teknoloji A.Ş. 2015 yılında İstanbul'da kurulmuştur ve merkez ofisi "
            "Maslak'tadır. Şirketin Ankara ve İzmir'de olmak üzere iki şube ofisi bulunmaktadır.",
            "El kitabıyla ilgili sorularınız için ik@ornekteknoloji.com adresine e-posta "
            "gönderebilir veya dahili 2400 numaralı hattı arayabilirsiniz.",
        ],
    ),
    (
        "2. Çalışma Saatleri",
        [
            "Standart çalışma saatleri hafta içi 09:00 ile 18:00 arasındadır. Öğle arası "
            "12:30 ile 13:30 arasında bir saattir.",
            "Şirket esnek çalışma modeli uygular: çalışanlar 10:00 ile 16:00 arasındaki "
            "çekirdek saatlerde çevrimiçi olmak koşuluyla mesailerine 07:30 ile 10:00 "
            "arasında herhangi bir saatte başlayabilirler.",
            "Fazla mesai, yöneticinin yazılı onayı ile yapılır. Fazla mesai ücreti normal "
            "saatlik ücretin yüzde 50 fazlası olarak hesaplanır.",
        ],
    ),
    (
        "3. Uzaktan Çalışma Politikası",
        [
            "Çalışanlar haftada en fazla 3 gün uzaktan çalışabilir. Salı ve Perşembe günleri "
            "tüm ekipler için ofis günü olarak belirlenmiştir.",
            "Uzaktan çalışan personele her ay 1.500 TL internet ve elektrik desteği ödenir. "
            "Bu destek maaşla birlikte ayın son iş gününde hesaba yatırılır.",
            "Yurt dışından uzaktan çalışma yılda en fazla 30 gün ile sınırlıdır ve İK "
            "Departmanı'ndan en az 2 hafta önce onay alınmasını gerektirir.",
        ],
    ),
    (
        "4. Yıllık İzin",
        [
            "Kıdemi 1 ile 5 yıl arasında olan çalışanlar yılda 14 iş günü, 5 ile 15 yıl "
            "arasında olanlar 20 iş günü, 15 yıldan fazla olanlar ise 26 iş günü ücretli "
            "yıllık izin hakkına sahiptir.",
            "Örnek Teknoloji A.Ş., yasal sürelere ek olarak tüm çalışanlara doğum günlerinde "
            "1 gün ek izin verir.",
            "İzin talepleri İK portalı üzerinden en az 5 iş günü önceden yapılmalıdır. "
            "Kullanılmayan izinlerin en fazla 5 günü bir sonraki yıla devredilebilir.",
        ],
    ),
    (
        "5. Hastalık ve Mazeret İzinleri",
        [
            "Hastalık durumunda çalışan, aynı gün saat 10:00'a kadar yöneticisine haber "
            "vermelidir. 2 günü aşan hastalık izinleri için doktor raporu zorunludur.",
            "Evlilik durumunda 5 gün, babalık izni olarak 10 gün, birinci derece yakının "
            "vefatı durumunda 5 gün ücretli mazeret izni verilir.",
        ],
    ),
    (
        "6. Masraf ve Harcırah",
        [
            "İş seyahatlerinde günlük yemek harcırahı yurt içinde 1.200 TL, yurt dışında "
            "75 Euro'dur. Konaklama için yurt içinde gecelik üst limit 4.000 TL'dir.",
            "Tüm masraflar, harcamanın yapıldığı tarihten itibaren 30 gün içinde fatura "
            "veya fişle birlikte masraf sistemine girilmelidir. Bu süreyi geçen masraflar "
            "ödenmez.",
            "5.000 TL üzerindeki tüm harcamalar için önceden departman direktörünün onayı "
            "gereklidir.",
        ],
    ),
    (
        "7. Eğitim ve Gelişim",
        [
            "Her çalışanın yıllık 15.000 TL eğitim bütçesi vardır. Bu bütçe kurs, "
            "sertifika, konferans ve kitap harcamaları için kullanılabilir.",
            "Şirket tarafından karşılanan ve bedeli 10.000 TL'yi aşan sertifika "
            "programlarına katılan çalışanlar, programın bitiminden itibaren en az 1 yıl "
            "şirkette çalışmayı taahhüt eder.",
        ],
    ),
    (
        "8. Yan Haklar",
        [
            "Tüm çalışanlar ve birinci derece aile üyeleri özel sağlık sigortası "
            "kapsamındadır. Sigorta poliçesi her yıl Mart ayında yenilenir.",
            "Çalışanlara iş günü başına 450 TL yemek kartı yüklemesi yapılır.",
            "Spor salonu üyeliği için aylık 1.000 TL'ye kadar destek sağlanır.",
        ],
    ),
    (
        "9. Bilgi Güvenliği",
        [
            "Şirket bilgisayarlarına yalnızca IT Departmanı tarafından onaylanmış yazılımlar "
            "kurulabilir. Şifreler en az 12 karakter olmalı ve her 90 günde bir "
            "değiştirilmelidir.",
            "Müşteri verileri hiçbir koşulda kişisel cihazlara veya kişisel bulut "
            "depolama hizmetlerine aktarılamaz. Şüpheli e-postalar guvenlik@ornekteknoloji.com "
            "adresine bildirilmelidir.",
        ],
    ),
]


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Title"], fontName="Arial-Bold")
    heading = ParagraphStyle("H", parent=styles["Heading2"], fontName="Arial-Bold")
    body = ParagraphStyle("B", parent=styles["BodyText"], fontName="Arial", fontSize=11, leading=15)

    story = [Paragraph("Örnek Teknoloji A.Ş. — Çalışan El Kitabı", title), Spacer(1, 0.5 * cm)]
    for i, (header, paragraphs) in enumerate(SECTIONS):
        story.append(Paragraph(header, heading))
        story.extend(Paragraph(p, body) for p in paragraphs)
        story.append(Spacer(1, 0.3 * cm))
        # Sayfa metadata'sını test edebilmek için birkaç bölümde bir sayfa sonu
        if i in (2, 5):
            story.append(PageBreak())

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, title="Çalışan El Kitabı")
    doc.build(story)
    print(f"Oluşturuldu: {OUTPUT}")


if __name__ == "__main__":
    build()
