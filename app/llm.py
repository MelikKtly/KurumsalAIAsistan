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
        # Ollama cevap vermezse sonsuza kadar beklememek için (parçalar arası bekleme süresi).
        # Ölçüldü: multi-agent değerlendirmesinde bir istek 5+ dk cevapsız kaldı ve süreç dondu.
        client_kwargs={"timeout": settings.llm_read_timeout_s},
    )


# Agent için ayrı model nesnesi. Fark: düşünme (reasoning) modu AÇIK.
# Ölçüldü: qwen3 + Ollama'da reasoning=False iken bind_tools ile araç çağrısı istendiğinde
# model boş cevap dönüyor (ne araç çağrısı ne metin). reasoning=True'da araçları doğru çağırıyor;
# düşünme metni cevaba karışmaz, ayrı alanda (additional_kwargs["reasoning_content"]) gelir.
# RAG zinciri hız için düşünmesiz kalır (get_llm); agent planlama yaptığı için düşünmesi zaten faydalı.
@lru_cache
def get_agent_llm() -> BaseChatModel:
    """Araç kullanan agent için Ollama sohbet modeli (düşünme modu açık)."""
    settings = get_settings()
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        reasoning=True,
        # Çıktı token sınırı: sonsuz düşünme döngüsüne karşı koruma (bkz. config.agent_max_output_tokens)
        num_predict=settings.agent_max_output_tokens,
        # Ollama donarsa sonsuza kadar beklememek için (parçalar arası bekleme süresi)
        client_kwargs={"timeout": settings.llm_read_timeout_s},
    )

