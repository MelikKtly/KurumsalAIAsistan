"""FastAPI uygulaması: sistemin dışarıya açılan HTTP arayüzü.

Endpoint'ler:
    GET  /        → Sohbet arayüzü (HTML sayfası)
    GET  /health  → Sunucu ayakta mı kontrolü
    POST /ask     → Soru al, RAG ile kaynaklı cevap döndür
    GET  /docs    → FastAPI'nin otomatik ürettiği Swagger dokümantasyonu

Çalıştırma: uv run uvicorn app.api.main:app --reload
"""

from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from langchain_chroma import Chroma
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.retrieval.rag import RAGAnswer, answer_question
from app.vectorstore import get_vector_store

# Uygulama nesnesi; title/version /docs sayfasında görünür
app = FastAPI(title="Kurumsal AI Asistanı", version="0.1.0")

# Sohbet arayüzünün dosya yolu (bu dosyanın yanındaki static/ klasörü)
INDEX_HTML = Path(__file__).parent / "static" / "index.html"


class AskRequest(BaseModel):
    """`POST /ask` isteğinin gövdesi: {"question": "..."}."""

    # Field kısıtları FastAPI tarafından otomatik denetlenir: alan yoksa, boşsa veya
    # 1000 karakterden uzunsa istek endpoint'e ulaşmadan 422 hatası döner.
    # examples: /docs sayfasında "Try it out" için örnek değer.
    question: str = Field(min_length=1, max_length=1000, examples=["Yurt dışında yemek harcırahı ne kadar?"])


# --- Dependency'ler (bağımlılık enjeksiyonu) ---
# Endpoint LLM ve vektör veritabanını kendisi oluşturmaz; FastAPI bu fonksiyonları
# çağırıp sonucu parametre olarak verir. Testlerde app.dependency_overrides ile
# bunların yerine sahteleri (fake LLM, geçici Chroma) takılır; böylece testler
# Ollama'ya ve gerçek veritabanına ihtiyaç duymaz.
# (get_llm/get_vector_store doğrudan kullanılmadı: opsiyonel parametreleri olduğu için
# FastAPI onları HTTP sorgu parametresi sanıyordu; bu ince sarmalayıcılar parametresiz.)
def llm_dependency() -> BaseChatModel:
    return get_llm()


def vector_store_dependency() -> Chroma:
    return get_vector_store()


# include_in_schema=False: HTML sayfası bir API değil, /docs'ta listelenmesin
@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Sohbet arayüzü."""
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health() -> dict[str, str]:
    # İzleme araçları / Docker sağlık kontrolü için: sunucu cevap veriyorsa "ok"
    return {"status": "ok"}


# Dönüş tipi (RAGAnswer) FastAPI'ye cevabın şemasını söyler: JSON'a çevrilir ve /docs'ta gösterilir.
# Fonksiyon `async def` değil `def`: LLM çağrısı bloklayıcı olduğu için FastAPI bunu
# ayrı bir thread'de çalıştırır, sunucu bu sırada diğer istekleri karşılayabilir.
@app.post("/ask")
def ask(
    request: AskRequest,  # JSON gövdesi otomatik olarak AskRequest'e çevrilip doğrulanır
    # Annotated[Tip, Depends(f)]: "bu parametreyi f() çağırarak doldur"
    llm: Annotated[BaseChatModel, Depends(llm_dependency)],
    vector_store: Annotated[Chroma, Depends(vector_store_dependency)],
) -> RAGAnswer:
    """Soruyu dokümanlardan bulduğu bilgilerle, kaynak göstererek cevaplar."""
    # min_length=1 "   " (sadece boşluk) girdisini yakalamaz; onu burada reddediyoruz
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Soru boş olamaz")
    try:
        return answer_question(request.question, llm=llm, vector_store=vector_store)
    except (ConnectionError, httpx.ConnectError) as exc:
        # Ollama kapalıysa istemci httpx.ConnectError fırlatır. Kullanıcıya anlamsız bir
        # 500 yerine "servis geçici olarak kullanılamıyor" anlamındaki 503'ü açıklamayla dön.
        # `from exc`: orijinal hata loglarda zincir olarak görünsün (hata ayıklama için).
        raise HTTPException(status_code=503, detail="LLM servisine (Ollama) ulaşılamıyor") from exc
