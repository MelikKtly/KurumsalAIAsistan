"""FastAPI uygulaması: sistemin dışarıya açılan HTTP arayüzü.

Endpoint'ler:
    GET  /        → Sohbet arayüzü (HTML sayfası)
    GET  /health  → Sunucu ayakta mı kontrolü
    POST /ask     → Soru al, RAG ile kaynaklı cevap döndür
    POST /agent   → Görev al, araç kullanan agent (LangGraph) ile çöz
    GET  /docs    → FastAPI'nin otomatik ürettiği Swagger dokümantasyonu

Her /ask ve /agent isteği veritabanındaki query_logs tablosuna kaydedilir (Faz 4.2).

Çalıştırma: uv run uvicorn app.api.main:app --reload
"""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from langchain_chroma import Chroma
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.graph import run_graph_agent
from app.agent.simple_agent import AgentResult
from app.config import get_settings
from app.cost import estimate_cost
from app.db import QueryLog, get_session, init_db
from app.llm import get_agent_llm, get_llm
from app.logging_config import setup_logging
from app.observability import append_request_log, timer
from app.retrieval.rag import RAGAnswer, answer_question
from app.vectorstore import get_vector_store


logger = logging.getLogger("app.api")


# lifespan: uygulama açılırken (yield'den önce) ve kapanırken (sonra) çalışan kod.
# Açılışta tablolar yoksa oluşturulur ve örnek çalışan verisi eklenir.
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(get_settings().log_level)
    init_db()
    logger.info("app_started", extra={"llm_model": get_settings().llm_model})
    yield


# Uygulama nesnesi; title/version /docs sayfasında görünür
app = FastAPI(title="Kurumsal AI Asistanı", version="0.2.0", lifespan=lifespan)

# Sohbet arayüzünün dosya yolu (bu dosyanın yanındaki static/ klasörü)
INDEX_HTML = Path(__file__).parent / "static" / "index.html"

# Middleware: her HTTP isteğinin etrafında çalışan kod. Her isteğe benzersiz bir request_id verir,
# süresini ölçer ve sonunda tek bir yapılandırılmış log satırı yazar. request_id cevap başlığında
# (X-Request-ID) da döner; kullanıcı bir hata bildirdiğinde loglarda o isteği bulmayı sağlar.
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    with timer() as t:
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    # 5xx → ERROR, 4xx → WARNING, diğerleri → INFO
    level = logging.ERROR if response.status_code >= 500 else logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(level, "request_finished", extra={
        "request_id": request_id, "method": request.method, "path": request.url.path,
        "status": response.status_code, "duration_ms": t["ms"],
    })
    return response


# Ollama kapalıyken LLM istemcisinin fırlattığı hatalar → 503
LLM_CONNECTION_ERRORS = (ConnectionError, httpx.ConnectError)


class AskRequest(BaseModel):
    """`POST /ask` ve `POST /agent` isteğinin gövdesi: {"question": "..."}."""

    # Field kısıtları FastAPI tarafından otomatik denetlenir: alan yoksa, boşsa veya
    # 1000 karakterden uzunsa istek endpoint'e ulaşmadan 422 hatası döner.
    # examples: /docs sayfasında "Try it out" için örnek değer.
    question: str = Field(min_length=1, max_length=1000, examples=["Yurt dışında yemek harcırahı ne kadar?"])


# --- Dependency'ler (bağımlılık enjeksiyonu) ---
# Endpoint LLM, vektör veritabanı ve SQL oturumunu kendisi oluşturmaz; FastAPI bu fonksiyonları
# çağırıp sonucu parametre olarak verir. Testlerde app.dependency_overrides ile bunların yerine
# sahteleri (fake LLM, geçici Chroma/SQLite) takılır; böylece testler Ollama'ya ve gerçek
# veritabanına ihtiyaç duymaz.
# (get_llm/get_vector_store doğrudan kullanılmadı: opsiyonel parametreleri olduğu için
# FastAPI onları HTTP sorgu parametresi sanıyordu; bu ince sarmalayıcılar parametresiz.)
def llm_dependency() -> BaseChatModel:
    return get_llm()


def agent_llm_dependency() -> BaseChatModel:
    return get_agent_llm()


def vector_store_dependency() -> Chroma:
    return get_vector_store()


def reject_blank(question: str) -> None:
    # min_length=1 "   " (sadece boşluk) girdisini yakalamaz; onu burada reddediyoruz
    if not question.strip():
        raise HTTPException(status_code=422, detail="Soru boş olamaz")


def save_query(session: Session, **fields) -> None:
    """İsteği query_logs tablosuna yazar (Faz 4.2: sorgu geçmişi, araçlar, maliyet/latency)."""
    session.add(QueryLog(llm_model=get_settings().llm_model, **fields))
    session.commit()


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
    session: Annotated[Session, Depends(get_session)],
) -> RAGAnswer:
    """Soruyu dokümanlardan bulduğu bilgilerle, kaynak göstererek cevaplar."""
    reject_blank(request.question)
    settings = get_settings()
    # Hata durumunda da ne kadar beklendiğini loglayabilmek için tüm isteği ölç
    with timer() as t:
        try:
            result = answer_question(request.question, llm=llm, vector_store=vector_store)
        except LLM_CONNECTION_ERRORS as exc:
            error = exc
        else:
            error = None

    if error is not None:
        append_request_log(
            {"status": "error", "error": "llm_unreachable", "question": request.question, "total_ms": t["ms"]},
            settings.request_log_path,
        )
        save_query(session, endpoint="ask", status="error", question=request.question, total_ms=t["ms"])
        # Ollama kapalıysa istemci httpx.ConnectError fırlatır. Kullanıcıya anlamsız bir
        # 500 yerine "servis geçici olarak kullanılamıyor" anlamındaki 503'ü açıklamayla dön.
        # `from error`: orijinal hata loglarda zincir olarak görünsün (hata ayıklama için).
        logger.error("llm_unreachable", extra={"endpoint": "/ask", "error": type(error).__name__})
        raise HTTPException(status_code=503, detail="LLM servisine (Ollama) ulaşılamıyor") from error

    # Başarılı istek: analiz için gereken alanlar (cevap metninin tamamı ve kaynaklar loglanmaz;
    # amaç performans/maliyet ölçümü). model_dump: Pydantic nesnesini sözlüğe çevirir.
    append_request_log(
        {
            "status": "ok",
            "question": request.question,
            "answer_type": result.answer_type,
            "prompt_version": result.prompt_version,
            "llm_model": settings.llm_model,
            "grounded": result.groundedness.grounded if result.groundedness else None,
            "metrics": result.metrics.model_dump(),
        },
        settings.request_log_path,
    )
    m = result.metrics
    save_query(
        session,
        endpoint="ask",
        status="ok",
        question=request.question,
        answer=result.answer,
        answer_type=result.answer_type,
        grounded=result.groundedness.grounded if result.groundedness else None,
        prompt_version=result.prompt_version,
        llm_calls=1 + (1 if m.grounding_ms is not None else 0),  # cevap + varsa hakem
        total_ms=m.total_ms,
        input_tokens=m.total_tokens.input_tokens,
        output_tokens=m.total_tokens.output_tokens,
        cost_usd=m.cost.usd if m.cost else None,
        reference_cost_usd=m.cost.reference_usd if m.cost else None,
    )
    return result


class AgentResponse(AgentResult):
    """`POST /agent` cevabı: agent sonucu + maliyet tahmini."""

    cost_usd: float | None
    reference_model: str
    reference_cost_usd: float | None


@app.post("/agent")
def agent(
    request: AskRequest,
    llm: Annotated[BaseChatModel, Depends(agent_llm_dependency)],
    session: Annotated[Session, Depends(get_session)],
) -> AgentResponse:
    """Görevi araç kullanan agent'la çözer (doküman arama, döviz kuru, çalışan veritabanı).

    Cevapta hangi araçların hangi sırayla, hangi girdilerle çağrıldığı (steps) ve adım adım iz
    (trace) da döner. Çok adımlı görevler 1–3 dakika sürebilir.
    """
    reject_blank(request.question)
    settings = get_settings()
    try:
        result = run_graph_agent(request.question, llm=llm)
    except LLM_CONNECTION_ERRORS as exc:
        save_query(session, endpoint="agent", status="error", question=request.question, total_ms=0)
        logger.error("llm_unreachable", extra={"endpoint": "/agent", "error": type(exc).__name__})
        raise HTTPException(status_code=503, detail="LLM servisine (Ollama) ulaşılamıyor") from exc

    cost = estimate_cost(result.tokens, settings.llm_model, settings.cost_reference_model)
    logger.info("agent_finished", extra={
        "tools": [s.tool for s in result.steps], "llm_calls": result.llm_calls,
        "stop_reason": result.stop_reason, "duration_ms": result.total_ms, "tokens": result.tokens.total_tokens,
    })
    if result.stop_reason != "done":
        # Adım/çıktı limiti: sistem cevap verdi ama görev tam tamamlanmamış olabilir
        logger.warning("agent_limit_reached", extra={"stop_reason": result.stop_reason})
    save_query(
        session,
        endpoint="agent",
        status="ok",
        question=request.question,
        answer=result.answer,
        prompt_version=settings.agent_prompt_version,
        tools_used=[s.tool for s in result.steps],
        llm_calls=result.llm_calls,
        total_ms=result.total_ms,
        input_tokens=result.tokens.input_tokens,
        output_tokens=result.tokens.output_tokens,
        cost_usd=cost.usd,
        reference_cost_usd=cost.reference_usd,
    )
    return AgentResponse(
        **result.model_dump(),
        cost_usd=cost.usd,
        reference_model=cost.reference_model,
        reference_cost_usd=cost.reference_usd,
    )
