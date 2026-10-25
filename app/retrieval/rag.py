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


class Source(BaseModel):
    ref: int
    source: str
    page: int
    chunk_id: int
    score: float
    snippet: str


class RAGAnswer(BaseModel):
    question: str
    answer: str
    sources: list[Source]
    prompt_version: str


def format_context(documents: list[Document]) -> str:
    """Chunk'ları LLM'in [n] ile atıf yapabileceği numaralı bloklara çevirir."""
    blocks = []
    for i, doc in enumerate(documents, start=1):
        m = doc.metadata
        blocks.append(f"[{i}] ({Path(m['source']).name}, sayfa {m['page'] + 1})\n{doc.page_content}")
    return "\n\n".join(blocks)


def to_sources(documents: list[Document]) -> list[Source]:
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
    chain = prompt.template | (llm or get_llm()) | StrOutputParser()
    return chain.invoke({"context": format_context(documents), "question": question}).strip()


def answer_question(
    question: str,
    llm: BaseChatModel | None = None,
    vector_store: Chroma | None = None,
    prompt: PromptSpec | None = None,
) -> RAGAnswer:
    """Soruya ilgili chunk'ları bulup LLM ile kaynaklı cevap üretir.

    `prompt` verilmezse aktif versiyon kullanılır; karşılaştırma için farklı bir
    versiyon geçilebilir.
    """
    prompt = prompt or get_rag_prompt()
    documents = retrieve(question, vector_store=vector_store)
    return RAGAnswer(
        question=question,
        answer=generate_answer(question, documents, llm=llm, prompt=prompt),
        sources=to_sources(documents),
        prompt_version=prompt.version,
    )
