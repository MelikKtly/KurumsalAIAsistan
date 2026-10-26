"""Metin yardımcıları (uygulamanın farklı yerlerinde ortak kullanılır)."""


def normalize(text: str) -> str:
    """Büyük/küçük harf duyarsız karşılaştırma için metni küçük harfe çevirir."""
    # Python'un lower()'ı Türkçeyi bilmez: "İ".lower() → "i̇" (i + birleşik nokta),
    # "I".lower() → "i" (Türkçede "ı" olmalı). Önce bu iki harfi elle düzeltiyoruz.
    return text.replace("İ", "i").replace("I", "ı").lower()
