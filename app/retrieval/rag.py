"""RAG zinciri: retrieval + LLM ile kaynak gösteren cevap üretimi.

Akış:  soru → retrieve() → numaralı bağlam ([1], [2]...) → prompt → LLM → cevap
Cevapla birlikte kullanılan chunk'lar da "kaynak" olarak döner; böylece kullanıcı
cevaptaki [n] atıfının hangi dosya ve sayfadan geldiğini görebilir.
"""

from pathlib import Path
from typing import Literal

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_chroma import Chroma
from pydantic import BaseModel

from app.config import get_settings
from app.llm import get_llm
from app.observability import RequestMetrics, TokenUsage, timer
from app.prompts.loader import PromptSpec, load_prompt
from app.retrieval.citations import extract_citations, valid_refs
from app.retrieval.context import format_context
from app.retrieval.groundedness import GroundednessVerdict, check_groundedness
from app.retrieval.retriever import retrieve
from app.text import normalize

# Cevabın türü — arayüz ve istemciler buna göre davranır (örn. kaynakları gösterip göstermemek):
#   answered  → dokümanlardan, en az bir geçerli atıfla cevaplandı
#   not_found → şirket sorusu ama cevap dokümanlarda yok ("bilmiyorum" fallback'i)
#   off_topic → şirketle ilgisiz mesaj, cevaplanmadı
#   uncited   → sabit kalıp da değil, geçerli atıf da yok (örn. selamlaşma cevabı,
#               ya da modelin kaynaksız verdiği bir cevap — ikincisi güvenilmez sayılmalı)
AnswerType = Literal["answered", "not_found", "off_topic", "uncited"]


# Pydantic modelleri: veri yapısını ve tiplerini tanımlar. FastAPI bunları
# otomatik olarak JSON'a çevirir ve /docs sayfasında şema olarak gösterir.
class Source(BaseModel):
    """Cevapta kullanılan bir kaynak (arayüzdeki kaynak kartı)."""

    ref: int  # Cevaptaki atıf numarası: [1] → ref=1
    source: str  # Dosya adı (tam yol değil)
    page: int  # Kullanıcıya gösterilen sayfa no (1'den başlar)
    chunk_id: int
    score: float  # Cosine uzaklığı (küçük = daha ilgili)
    snippet: str  # Chunk metninin ilk 200 karakteri (önizleme)
    cited: bool = False  # Cevapta bu kaynağa [ref] ile atıf yapıldı mı


class RAGAnswer(BaseModel):
    """`POST /ask` cevabının yapısı."""

    question: str
    answer: str
    answer_type: AnswerType
    # Retrieval'ın getirdiği tüm chunk'lar (atıf yapılmasa da şeffaflık için döner;
    # hangilerinin kullanıldığı Source.cited ile belli)
    sources: list[Source]
    prompt_version: str  # Bu cevabı hangi prompt versiyonu üretti (loglama/karşılaştırma için)
    # Hakemin kararı. None: kontrol kapalı, cevap kaynaklı değil (answered dışı) veya hakem
    # geçerli bir karar üretemedi. İstemci None'ı "doğrulanmadı" olarak yorumlamalı.
    groundedness: GroundednessVerdict | None = None
    metrics: RequestMetrics  # Adım adım süreler ve token kullanımı


def to_sources(documents: list[Document]) -> list[Source]:
    """Chunk'ları API cevabındaki kaynak listesine çevirir (numaralar format_context ile aynı)."""
    return [
        Source(
            ref=i,
            source=Path(d.metadata["source"]).name,
            page=d.metadata["page"] + 1,  # Kullanıcıya 1'den başlayan sayfa no
            chunk_id=d.metadata["chunk_id"],
            score=d.metadata["score"],
            snippet=d.page_content[:200],
        )
        for i, d in enumerate(documents, start=1)
    ]


def classify_answer(answer: str, prompt: PromptSpec, n_sources: int) -> tuple[AnswerType, set[int]]:
    """Cevabın türünü ve geçerli atıf numaralarını belirler.

    Sabit cevap kalıpları prompt dosyasındaki `fixed_replies`'tan okunur; böylece
    prompt metni değişse bile tespit kuralı otomatik olarak güncel kalır.
    Dönüş: (cevap türü, atıf yapılan kaynak numaraları — örn. {1, 3})
    """
    text = normalize(answer)
    # Model sabit cevabın başına/sonuna bir şey ekleyebilir ("Maalesef, bu bilgi
    # dokümanlarda yer almıyor [1]") — bu yüzden birebir eşitlik değil, "içeriyor mu" kontrolü.
    # fixed_replies yoksa (örn. v1 promptu) .get() None döner ve bu kontroller atlanır.
    not_found = prompt.fixed_replies.get("not_found")
    off_topic = prompt.fixed_replies.get("off_topic")
    if not_found and normalize(not_found) in text:
        # "Bilmiyorum" cevabındaki olası atıf anlamsız (bilgi o kaynakta yok) → atıf sayılmaz
        return "not_found", set()
    if off_topic and normalize(off_topic) in text:
        return "off_topic", set()

    refs = valid_refs(extract_citations(answer), n_sources)
    # Geçerli en az bir atıf varsa cevap kaynağa dayanıyor; yoksa kaynaksız
    return ("answered" if refs else "uncited"), refs


def get_rag_prompt() -> PromptSpec:
    """`.env`'deki RAG_PROMPT_VERSION'a göre aktif RAG promptu."""
    return load_prompt("rag", get_settings().rag_prompt_version)


class Generation(BaseModel):
    """generate_answer'ın dönüşü: cevap metni + bu LLM çağrısının token kullanımı."""

    text: str
    usage: TokenUsage


def generate_answer(
    question: str,
    documents: list[Document],
    llm: BaseChatModel | None = None,
    prompt: PromptSpec | None = None,
) -> Generation:
    """Verilen chunk'larla (retrieval yapmadan) cevap üretir.

    Aynı chunk'ları farklı prompt/model ile denemek için ayrı tutuldu.
    """
    prompt = prompt or get_rag_prompt()
    # LCEL (LangChain Expression Language): `|` ile adımlar zincirlenir, her adımın
    # çıktısı bir sonrakinin girdisi olur:
    #   prompt şablonu → {context, question}'ı doldurup mesaj listesi üretir
    #   LLM            → mesajları modele gönderir, AIMessage döner
    # (Önceden sona StrOutputParser ekleyip sadece metni alıyorduk; artık AIMessage'ın
    # tamamını alıyoruz çünkü token sayıları mesajın usage_metadata alanında.)
    chain = prompt.template | (llm or get_llm())
    # invoke: zinciri çalıştırır; sözlükteki anahtarlar prompttaki {değişken}'lere karşılık gelir
    message = chain.invoke({"context": format_context(documents), "question": question})
    return Generation(text=message.content.strip(), usage=TokenUsage.from_message(message))


def answer_question(
    question: str,
    # Aşağıdakiler opsiyonel: normalde gerçek LLM/Chroma/aktif prompt kullanılır;
    # testler sahte model ve geçici veritabanı, eval scripti farklı prompt verir.
    llm: BaseChatModel | None = None,
    vector_store: Chroma | None = None,
    prompt: PromptSpec | None = None,
    # None ise .env'deki GROUNDEDNESS_CHECK ayarı kullanılır
    check_grounding: bool | None = None,
) -> RAGAnswer:
    """Soruya ilgili chunk'ları bulup LLM ile kaynaklı cevap üretir.

    `prompt` verilmezse aktif versiyon kullanılır; karşılaştırma için farklı bir
    versiyon geçilebilir.
    """
    prompt = prompt or get_rag_prompt()
    # Her adım timer() ile ölçülür; t["ms"] bloğun süresi (milisaniye)
    with timer() as total_t:
        # 1) Retrieval: en ilgili top_k chunk
        with timer() as retrieval_t:
            documents = retrieve(question, vector_store=vector_store)
        # 2) Generation: chunk'ları bağlam olarak verip cevap üret
        with timer() as generation_t:
            generation = generate_answer(question, documents, llm=llm, prompt=prompt)
        answer = generation.text
        # 3) Cevabı sınıflandır ve hangi kaynaklara atıf yapıldığını işaretle
        answer_type, cited_refs = classify_answer(answer, prompt, len(documents))
        sources = to_sources(documents)
        for source in sources:
            source.cited = source.ref in cited_refs

        # 4) (Opsiyonel) Groundedness: yalnızca dokümanlara dayandığını iddia eden cevaplar
        # denetlenir. "Bilgi yok", konu dışı ve selamlaşma cevaplarında doğrulanacak iddia yok.
        if check_grounding is None:
            check_grounding = get_settings().groundedness_check
        grounding = None
        grounding_ms = None
        if check_grounding and answer_type == "answered":
            # Hakem için de aynı LLM kullanılır (testlerde verilen sahte model dahil)
            with timer() as grounding_t:
                grounding = check_groundedness(question, answer, documents, llm=llm)
            grounding_ms = grounding_t["ms"]

    return RAGAnswer(
        question=question,
        answer=answer,
        answer_type=answer_type,
        sources=sources,
        prompt_version=prompt.version,
        groundedness=grounding.verdict if grounding else None,
        metrics=RequestMetrics(
            retrieval_ms=retrieval_t["ms"],
            generation_ms=generation_t["ms"],
            grounding_ms=grounding_ms,
            total_ms=total_t["ms"],
            generation_tokens=generation.usage,
            grounding_tokens=grounding.usage if grounding else None,
        ),
    )
