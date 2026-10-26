"""RAG zinciri: retrieval + LLM ile kaynak gösteren cevap üretimi.

Akış:  soru → retrieve() → numaralı bağlam ([1], [2]...) → prompt → LLM → cevap
Cevapla birlikte kullanılan chunk'lar da "kaynak" olarak döner; böylece kullanıcı
cevaptaki [n] atıfının hangi dosya ve sayfadan geldiğini görebilir.
"""

from pathlib import Path
from typing import Literal

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from pydantic import BaseModel

from app.config import get_settings
from app.llm import get_llm
from app.prompts.loader import PromptSpec, load_prompt
from app.retrieval.citations import extract_citations, valid_refs
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


def format_context(documents: list[Document]) -> str:
    """Chunk'ları LLM'in [n] ile atıf yapabileceği numaralı bloklara çevirir."""
    # Üretilen metin örneği:
    #   [1] (ornek_ik_el_kitabi.pdf, sayfa 2)
    #   4. Yıllık İzin ...
    #
    #   [2] (ornek_ik_el_kitabi.pdf, sayfa 1)
    #   ...
    # LLM'e "kaynağı [n] ile belirt" dediğimiz için numaralar buradan geliyor.
    blocks = []
    for i, doc in enumerate(documents, start=1):
        m = doc.metadata
        # page metadata'da 0'dan başlıyor; insanlar için +1
        blocks.append(f"[{i}] ({Path(m['source']).name}, sayfa {m['page'] + 1})\n{doc.page_content}")
    return "\n\n".join(blocks)


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


def generate_answer(
    question: str,
    documents: list[Document],
    llm: BaseChatModel | None = None,
    prompt: PromptSpec | None = None,
) -> str:
    """Verilen chunk'larla (retrieval yapmadan) cevap üretir.

    Aynı chunk'ları farklı prompt/model ile denemek için ayrı tutuldu.
    """
    prompt = prompt or get_rag_prompt()
    # LCEL (LangChain Expression Language): `|` ile adımlar zincirlenir, her adımın
    # çıktısı bir sonrakinin girdisi olur:
    #   prompt şablonu  → {context, question}'ı doldurup mesaj listesi üretir
    #   LLM             → mesajları modele gönderir, AIMessage döner
    #   StrOutputParser → AIMessage'tan sadece metni çıkarır
    chain = prompt.template | (llm or get_llm()) | StrOutputParser()
    # invoke: zinciri çalıştırır; sözlükteki anahtarlar prompttaki {değişken}'lere karşılık gelir
    return chain.invoke({"context": format_context(documents), "question": question}).strip()


def answer_question(
    question: str,
    # Aşağıdakiler opsiyonel: normalde gerçek LLM/Chroma/aktif prompt kullanılır;
    # testler sahte model ve geçici veritabanı, eval scripti farklı prompt verir.
    llm: BaseChatModel | None = None,
    vector_store: Chroma | None = None,
    prompt: PromptSpec | None = None,
) -> RAGAnswer:
    """Soruya ilgili chunk'ları bulup LLM ile kaynaklı cevap üretir.

    `prompt` verilmezse aktif versiyon kullanılır; karşılaştırma için farklı bir
    versiyon geçilebilir.
    """
    prompt = prompt or get_rag_prompt()
    # 1) Retrieval: en ilgili top_k chunk
    documents = retrieve(question, vector_store=vector_store)
    # 2) Generation: chunk'ları bağlam olarak verip cevap üret
    answer = generate_answer(question, documents, llm=llm, prompt=prompt)
    # 3) Cevabı sınıflandır ve hangi kaynaklara atıf yapıldığını işaretle
    answer_type, cited_refs = classify_answer(answer, prompt, len(documents))
    sources = to_sources(documents)
    for source in sources:
        source.cited = source.ref in cited_refs
    return RAGAnswer(
        question=question,
        answer=answer,
        answer_type=answer_type,
        sources=sources,
        prompt_version=prompt.version,
    )
