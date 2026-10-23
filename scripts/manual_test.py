"""Faz 1 elle test: örnek PDF üzerinde soru setini çalıştırıp sonuçları JSON'a yazar.

Değerlendirme (doğru mu, kaynak doğru mu) elle yapılır; sonuçlar docs/faz1_elle_test.md'de.

Kullanım:
    uv run python -m scripts.manual_test [çıktı.json]
"""

import json
import sys
import time

from app.retrieval.rag import answer_question

# (kategori, soru, beklenen cevap, cevabın bulunduğu chunk_id veya None)
QUESTIONS = [
    ("doğrudan", "Standart çalışma saatleri nedir?", "Hafta içi 09:00–18:00", 0),
    ("doğrudan", "Fazla mesai ücreti nasıl hesaplanır?", "Saatlik ücretin %50 fazlası, yönetici yazılı onayıyla", 1),
    ("doğrudan", "Uzaktan çalışanlara internet desteği ne kadar?", "Aylık 1.500 TL", 1),
    ("doğrudan", "Babalık izni kaç gün?", "10 gün", 2),
    ("doğrudan", "Yurt içinde konaklama için gecelik limit nedir?", "4.000 TL", 3),
    ("doğrudan", "Yıllık eğitim bütçem ne kadar?", "15.000 TL", 4),
    ("doğrudan", "Spor salonu için destek var mı?", "Aylık 1.000 TL'ye kadar", 4),
    ("doğrudan", "Şifrem en az kaç karakter olmalı?", "En az 12 karakter", 4),
    ("çıkarım", "Mesaiye en geç saat kaçta başlayabilirim?", "10:00", 0),
    ("çıkarım", "Kıdemim 3 yıl, kaç gün yıllık iznim var?", "14 iş günü (+ doğum günü izni)", 2),
    ("çıkarım", "3 gün hasta olursam doktor raporu gerekir mi?", "Evet, 2 günü aşan izinlerde zorunlu", 2),
    ("çıkarım", "6.000 TL'lik bir harcama için onay almam gerekir mi?", "Evet, departman direktöründen önceden", 3),
    ("çıkarım", "12.000 TL'lik bir sertifikayı şirket ödedi, bitirince hemen ayrılabilir miyim?", "Hayır, en az 1 yıl çalışma taahhüdü var", 4),
    ("çıkarım", "Hangi günler ofiste olmam gerekiyor?", "Salı ve Perşembe", 1),
    ("yok", "Şirketin CEO'su kim?", "Dokümanda yok", None),
    ("yok", "Maaş zamları hangi ay yapılıyor?", "Dokümanda yok", None),
    ("yok", "Şirket araba veriyor mu?", "Dokümanda yok", None),
    ("kısmen", "Ankara ofisinin adresi nedir?", "Ankara'da şube var, adres dokümanda yok", None),
]


def main(output: str) -> None:
    results = []
    for category, question, expected, chunk in QUESTIONS:
        start = time.perf_counter()
        result = answer_question(question)
        elapsed = time.perf_counter() - start
        retrieved = [s.chunk_id for s in result.sources]
        results.append(
            {
                "category": category,
                "question": question,
                "expected": expected,
                "answer": result.answer,
                "expected_chunk": chunk,
                "retrieved_chunks": retrieved,
                "expected_chunk_rank": retrieved.index(chunk) + 1 if chunk in retrieved else None,
                "top_score": result.sources[0].score,
                "seconds": round(elapsed, 1),
            }
        )
        print(f"[{elapsed:4.1f} sn] {question}\n          → {result.answer}\n")

    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Sonuçlar: {output}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "faz1_sonuclar.json")
