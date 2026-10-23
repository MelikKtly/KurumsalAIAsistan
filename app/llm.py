from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from app.config import get_settings


@lru_cache
def get_llm() -> BaseChatModel:
    """Cevap üretimi için Ollama sohbet modeli."""
    settings = get_settings()
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,  # Aynı soruya tutarlı cevap; RAG'de yaratıcılık istemiyoruz
        reasoning=False,  # qwen3'ün <think> modunu kapat: daha hızlı, cevapta düşünce metni olmaz
    )
