"""Agent'ın kullanabileceği araçlar (tools).

Araç = LLM'in çağırmaya karar verebileceği bir Python fonksiyonu. `@tool` dekoratörü
fonksiyonun adını, docstring'ini ve parametre tiplerini bir JSON şemasına çevirir;
model bu şemayı görür ve "şu aracı şu argümanlarla çağır" diye yapılandırılmış bir
istek (tool_call) üretir. Fonksiyonu modeli değil, BİZİM kodumuz çalıştırır.

Docstring'ler modelin aracı ne zaman kullanacağına karar verirken okuduğu metindir —
bu yüzden "ne işe yarar / ne zaman kullanılır" net yazılmalıdır.
"""

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.retrieval.context import format_context
from app.retrieval.retriever import retrieve


@tool
def search_documents(query: str) -> str:
    """Şirket dokümanlarında (çalışan el kitabı: izinler, masraflar, harcırah, yan haklar,
    çalışma saatleri, uzaktan çalışma, bilgi güvenliği) anlamsal arama yapar.
    Şirket kuralları veya politikalarıyla ilgili her bilgi için bu aracı kullan.
    Dönen metindeki [n] numaralarını cevapta kaynak olarak gösterebilirsin."""
    # Faz 1'deki retrieval fonksiyonunun aynısı; sadece araç olarak sarıldı.
    # Sonuç LLM'e metin olarak döner: RAG'deki numaralı bağlam formatı.
    documents = retrieve(query)
    return format_context(documents)


@tool
def get_exchange_rate(base: str, target: str = "TRY") -> str:
    """Güncel döviz kurunu döndürür (Avrupa Merkez Bankası verisi).
    base ve target üç harfli para birimi kodlarıdır, örn. base="EUR", target="TRY".
    Bir tutarı başka para birimine çevirmek için önce bu aracı kullan."""
    base, target = base.upper().strip(), target.upper().strip()
    try:
        response = httpx.get(
            get_settings().exchange_api_url,
            params={"base": base, "symbols": target},
            timeout=10,
            follow_redirects=True,
        )
        response.raise_for_status()  # 4xx/5xx → HTTPStatusError
        data = response.json()
        rate = data["rates"][target]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        # Araç hatası exception olarak agent'ı çökertmemeli: modele metin olarak bildirilir,
        # model de kullanıcıya "kur alınamadı" diyebilir veya farklı bir yol dener.
        return f"HATA: {base}/{target} kuru alınamadı ({type(exc).__name__})."
    return f"1 {base} = {rate} {target} (tarih: {data['date']}, kaynak: Avrupa Merkez Bankası)"


# Agent'a verilen araç listesi
TOOLS = [search_documents, get_exchange_rate]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
