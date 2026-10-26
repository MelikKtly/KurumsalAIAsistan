import pytest

from app.prompts.loader import load_prompt
from app.retrieval.citations import extract_citations, valid_refs
from app.retrieval.rag import classify_answer

V2 = load_prompt("rag", "v2")  # fixed_replies içeren prompt
V1 = load_prompt("rag", "v1")  # fixed_replies yok
NOT_FOUND = V2.fixed_replies["not_found"]
OFF_TOPIC = V2.fixed_replies["off_topic"]


def test_extract_and_validate_citations():
    cites = extract_citations("75 Euro [1]. Ayrıca [K1] ve [7], tekrar [1].")
    assert cites == ["1", "K1", "7", "1"]
    # 4 kaynak varken yalnızca 1..4 aralığındaki sayılar geçerli
    assert valid_refs(cites, n_sources=4) == {1}


@pytest.mark.parametrize(
    "answer, expected_type, expected_refs",
    [
        ("Yurt dışında 75 Euro'dur [1].", "answered", {1}),
        ("Salı [2] ve Perşembe [3].", "answered", {2, 3}),
        (NOT_FOUND, "not_found", set()),
        # Model sabit cevabı süsleyip atıf eklese bile "bilmiyorum" olarak tanınmalı, atıf sayılmamalı
        (f"Maalesef, {NOT_FOUND.lower()} [1]", "not_found", set()),
        (OFF_TOPIC, "off_topic", set()),
        ("İyiyim, size nasıl yardımcı olabilirim?", "uncited", set()),
        # Sadece geçersiz atıf varsa kaynaklı cevap sayılmaz
        ("75 Euro [K1]", "uncited", set()),
    ],
)
def test_classify_answer_v2(answer, expected_type, expected_refs):
    assert classify_answer(answer, V2, n_sources=4) == (expected_type, expected_refs)


def test_classify_answer_without_fixed_replies():
    # v1'de sabit kalıp yok: "bilmiyorum" metni tanınamaz, atıf yoksa "uncited" olur
    assert classify_answer("Bağlamda bu bilgi yok.", V1, n_sources=4) == ("uncited", set())
    assert classify_answer("10 gün [1]", V1, n_sources=4) == ("answered", {1})
