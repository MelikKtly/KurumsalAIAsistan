"""Uygulamanın tüm ayarları tek yerde.

Ayarlar koda gömülmez; proje kökündeki `.env` dosyasından okunur. Böylece model,
chunk boyutu, prompt versiyonu gibi değerler kod değiştirmeden değiştirilebilir.
Öncelik sırası: ortam değişkeni > .env dosyası > aşağıdaki varsayılan değer.
Örn. `LLM_MODEL=qwen3:1.7b uv run ...` tek seferlik başka model kullanır.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# BaseSettings: alan adlarını büyük harfli ortam değişkenleriyle eşleştirir
# (llm_model ↔ LLM_MODEL) ve tipleri doğrular (örn. CHUNK_SIZE="abc" hata verir).
class Settings(BaseSettings):
    # env_file: ayarları .env'den oku; extra="ignore": .env'de tanımsız anahtar varsa hata verme
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM (cevap üreten model) ---
    ollama_base_url: str = "http://localhost:11434"  # Ollama'nın lokal API adresi
    llm_model: str = "qwen3:8b"  # `ollama list` ile görülen model adı

    # Hangi prompt dosyasının kullanılacağı: app/prompts/rag/<versiyon>.yaml
    rag_prompt_version: str = "v2"

    # Groundedness kontrolü: cevap üretildikten sonra ikinci bir LLM çağrısı (hakem)
    # cevabın bağlama dayanıp dayanmadığını denetler. Açıkken her cevap ~2 kat yavaşlar.
    groundedness_check: bool = True

    # --- Embedding (metni vektöre çeviren model) ---
    # Değiştirilirse Chroma'daki vektörler uyumsuz olur → ingest baştan yapılmalı
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # --- Vektör veritabanı ---
    chroma_dir: str = "data/chroma"  # Chroma'nın verisini yazdığı klasör (git'e girmez)
    chroma_collection: str = "kurumsal_docs"  # Koleksiyon ≈ SQL'deki tablo

    # --- Chunking ---
    chunk_size: int = 1000  # Bir parçanın en fazla karakter sayısı
    chunk_overlap: int = 150  # Ardışık parçaların ortak karakter sayısı (sınırda bilgi kaybolmasın)

    # --- Retrieval ---
    top_k: int = 4  # Her soruda LLM'e verilecek en yakın parça sayısı


# lru_cache: fonksiyon ilk çağrıldığında Settings oluşturulur (.env okunur), sonraki
# çağrılarda aynı nesne döner. Böylece dosya her istekte tekrar okunmaz.
@lru_cache
def get_settings() -> Settings:
    return Settings()
