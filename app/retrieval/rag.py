"""RAG zinciri: retrieval + LLM ile kaynak gösteren cevap üretimi.

Akış:  soru → retrieve() → numaralı bağlam ([1], [2]...) → prompt → LLM → cevap
Cevapla birlikte kullanılan chunk'lar da "kaynak" olarak döner; böylece kullanıcı
cevaptaki [n] atıfının hangi dosya ve sayfadan geldiğini görebilir.
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from pydantic import BaseModel

from app.config import get_settings
from app.llm import get_llm
from app.prompts.loader import PromptSpec, load_prompt
from app.retrieval.retriever import retrieve


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


class RAGAnswer(BaseModel):
    """`POST /ask` cevabının yapısı."""

    question: str
    answer: str
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
    # 2) Generation: chunk'ları bağlam olarak verip cevap üret, 3) kaynaklarla birlikte döndür
    return RAGAnswer(
        question=question,
        answer=generate_answer(question, documents, llm=llm, prompt=prompt),
        sources=to_sources(documents),
        prompt_version=prompt.version,
    )
