from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_settings


@lru_cache
def get_embeddings() -> Embeddings:
    """sentence-transformers embedding modelini yükler (ilk çağrıda indirir, sonra cache'ten)."""
    return HuggingFaceEmbeddings(
        model_name=get_settings().embedding_model,
        # Normalize edilmiş vektörlerde cosine benzerliği = iç çarpım
        encode_kwargs={"normalize_embeddings": True},
    )
