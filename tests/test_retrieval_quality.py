"""Retrieval kalite testi (Faz 4.5): gerçek embedding modeliyle doğru chunk bulunuyor mu?

Diğer testler sahte embedding kullanır (hızlı, modelsiz). Bu test GERÇEK modeli kullanır;
model bilgisayarda yoksa (örn. CI) otomatik atlanır — indirme ~470 MB.
"""

from pathlib import Path

import pytest

from app.config import get_settings
from app.evaluation.scoring import ANSWERABLE, load_eval_set

SAMPLE_PDF = Path("data/samples/ornek_ik_el_kitabi.pdf")
HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"


def embedding_model_cached() -> bool:
    # HuggingFace önbellek klasör adı: models--<kurum>--<model>
    name = "models--" + get_settings().embedding_model.replace("/", "--")
    return (HF_CACHE / name).is_dir()


pytestmark = pytest.mark.skipif(not embedding_model_cached(), reason="Embedding modeli indirilmemiş (CI)")


@pytest.fixture(scope="module")
def real_store(tmp_path_factory):
    from app.embeddings import get_embeddings
    from app.ingestion.pipeline import ingest_pdf
    from app.vectorstore import get_vector_store

    store = get_vector_store(embeddings=get_embeddings(), persist_directory=str(tmp_path_factory.mktemp("chroma")))
    ingest_pdf(SAMPLE_PDF, store)
    return store


def test_recall_at_k_on_dev_set(real_store):
    from app.retrieval.retriever import retrieve

    questions = [q for q in load_eval_set("data/eval/questions.yaml").questions if q.category in ANSWERABLE]
    found = []
    for q in questions:
        chunks = [d.metadata["chunk_id"] for d in retrieve(q.question, vector_store=real_store)]
        found.append(q.expected_chunk in chunks)
    recall = sum(found) / len(found)
    # Ölçülen değer 16/17 (yalnızca d01 "Standart çalışma saatleri" kaçıyor). Eşik, retrieval'ı
    # bozan bir değişikliği (embedding modeli, chunk ayarı) yakalayacak kadar sıkı.
    assert recall >= 15 / 17, f"recall@k = {sum(found)}/{len(found)}"


@pytest.mark.parametrize(
    "question, expected_text",
    [
        ("Yurt dışında yemek harcırahı ne kadar?", "75 Euro"),
        ("Tatil hakkım kaç gün?", "14 iş günü"),  # "tatil" kelimesi metinde yok: anlamsal eşleşme
        ("Babalık izni kaç gün?", "babalık izni"),
    ],
)
def test_top_result_contains_answer(real_store, question, expected_text):
    from app.retrieval.retriever import retrieve

    top = retrieve(question, k=1, vector_store=real_store)[0]
    assert expected_text.lower() in top.page_content.lower()
