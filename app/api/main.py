from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException
from langchain_chroma import Chroma
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.retrieval.rag import RAGAnswer, answer_question
from app.vectorstore import get_vector_store

app = FastAPI(title="Kurumsal AI Asistanı", version="0.1.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000, examples=["Yurt dışında yemek harcırahı ne kadar?"])


# Dependency'ler: testlerde app.dependency_overrides ile sahteleri enjekte edilir
def llm_dependency() -> BaseChatModel:
    return get_llm()


def vector_store_dependency() -> Chroma:
    return get_vector_store()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
def ask(
    request: AskRequest,
    llm: Annotated[BaseChatModel, Depends(llm_dependency)],
    vector_store: Annotated[Chroma, Depends(vector_store_dependency)],
) -> RAGAnswer:
    """Soruyu dokümanlardan bulduğu bilgilerle, kaynak göstererek cevaplar."""
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Soru boş olamaz")
    try:
        return answer_question(request.question, llm=llm, vector_store=vector_store)
    except (ConnectionError, httpx.ConnectError) as exc:
        raise HTTPException(status_code=503, detail="LLM servisine (Ollama) ulaşılamıyor") from exc
