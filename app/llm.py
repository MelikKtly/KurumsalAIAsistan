"""Cevap üreten LLM (büyük dil modeli) bağlantısı.

Şu an Ollama üzerinden lokal model kullanılıyor. Fonksiyon LangChain'in ortak
`BaseChatModel` tipini döndürdüğü için, ileride Claude'a geçmek sadece bu dosyada
ChatOllama yerine ChatAnthropic döndürmek demek; geri kalan kod değişmez.
"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from app.config import get_settings


# Model nesnesi bir kez oluşturulup tekrar kullanılır. (Modelin kendisi Ollama
# sunucusunda yüklü durur; bu nesne sadece ona istek atan istemcidir.)
@lru_cache
def get_llm() -> BaseChatModel:
    """Cevap üretimi için Ollama sohbet modeli."""
    settings = get_settings()
    return ChatOllama(
        model=settings.llm_model,  # örn. "qwen3:8b" — önceden `ollama pull` ile indirilmiş olmalı
        base_url=settings.ollama_base_url,
        temperature=0,  # Aynı soruya tutarlı cevap; RAG'de yaratıcılık istemiyoruz
        reasoning=False,  # qwen3'ün <think> modunu kapat: daha hızlı, cevapta düşünce metni olmaz
    )
