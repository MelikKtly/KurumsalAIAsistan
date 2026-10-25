"""Embedding modeli: metni anlamını temsil eden bir sayı listesine (vektöre) çevirir.

Hem ingest sırasında chunk'lar hem de her soruda soru bu modelle vektöre çevrilir.
İkisinin aynı modelle çevrilmesi şarttır; farklı modellerin vektörleri karşılaştırılamaz.
"""

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_settings


# Model diskten belleğe yüklenmesi birkaç saniye sürer (~470 MB). lru_cache sayesinde
# uygulama boyunca sadece bir kez yüklenir, sonraki çağrılar aynı nesneyi kullanır.
@lru_cache
def get_embeddings() -> Embeddings:
    """sentence-transformers embedding modelini yükler (ilk çağrıda indirir, sonra cache'ten)."""
    # HuggingFaceEmbeddings: sentence-transformers modelini LangChain'in ortak
    # Embeddings arayüzüne sarar; böylece Chroma onu doğrudan kullanabilir.
    # Model ilk kullanımda ~/.cache/huggingface/ altına indirilir.
    return HuggingFaceEmbeddings(
        model_name=get_settings().embedding_model,
        # Vektörlerin uzunluğunu 1'e ölçekle. Normalize edilmiş vektörlerde
        # cosine benzerliği = iç çarpım olur; karşılaştırma hem hızlı hem tutarlı olur.
        encode_kwargs={"normalize_embeddings": True},
    )
