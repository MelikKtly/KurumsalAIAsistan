from pathlib import Path

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from pydantic import BaseModel

from app.llm import get_llm
from app.retrieval.retriever import retrieve

# Sabit cevap kalıpları: arayüz/eval bu metinlerle "cevap yok" durumunu ayırt edebilir
OFF_TOPIC_REPLY = "Bu konuda yardımcı olamıyorum; yalnızca şirket dokümanlarıyla ilgili soruları cevaplayabiliyorum."
NOT_FOUND_REPLY = "Bu bilgi dokümanlarda yer almıyor."

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Sen Örnek Teknoloji A.Ş. çalışanlarının şirket dokümanlarıyla ilgili sorularını "
            "cevaplayan kurumsal asistansın. Türkçe ve kısa cevap ver.\n\n"
            "Kurallar:\n"
            "1. Mesaj selamlaşma, teşekkür veya hal hatır sorma ise (örn. 'merhaba', 'nasılsın', "
            "'teşekkürler') bağlamı kullanma; kısaca karşılık ver ve şirket dokümanlarıyla ilgili "
            "sorulara yardımcı olabileceğini söyle. Kaynak numarası yazma.\n"
            "2. Mesaj şirketle ilgili değilse (örn. hava durumu, fıkra, programlama, genel kültür) "
            "cevaplama, bağlamı kullanma ve yalnızca şunu yaz: "
            f'"{OFF_TOPIC_REPLY}"\n'
            "3. Şirketle ilgili bir soruysa yalnızca aşağıdaki bağlamdaki bilgileri kullan. "
            "Kullandığın bilginin kaynak numarasını cümlenin sonunda köşeli parantezle yaz, örn. [2].\n"
            "4. Şirketle ilgili soru bağlamda cevaplanmıyorsa yalnızca şunu yaz: "
            f'"{NOT_FOUND_REPLY}" Tahmin yürütme, bilgi uydurma.\n\n'
            "Bağlam:\n{context}",
        ),
        ("human", "{question}"),
    ]
)


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


def answer_question(
    question: str,
    llm: BaseChatModel | None = None,
    vector_store: Chroma | None = None,
) -> RAGAnswer:
    """Soruya ilgili chunk'ları bulup LLM ile kaynaklı cevap üretir."""
    documents = retrieve(question, vector_store=vector_store)
    chain = PROMPT | (llm or get_llm()) | StrOutputParser()
    answer = chain.invoke({"context": format_context(documents), "question": question})
    return RAGAnswer(question=question, answer=answer.strip(), sources=to_sources(documents))
