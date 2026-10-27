import pytest

from app.evaluation.scoring import EvalQuestion, contains_all, load_eval_set, score_answer

MARKERS = ["yer almıyor", "yardımcı olamıyorum"]
CHUNKS = [3, 1, 4, 2]  # retrieval sırası: [1]=chunk 3, [2]=chunk 1, ...


def q(category: str, must_contain=(), expected_chunk=None) -> EvalQuestion:
    return EvalQuestion(
        id="t", category=category, question="?", expected="",
        must_contain=list(must_contain), expected_chunk=expected_chunk,
    )


def test_contains_all_alternatives_and_turkish_case():
    assert contains_all("Salı ve PERŞEMBE", ["salı", "perşembe"])
    assert contains_all("Hayır, bir yıl kalmalısınız", ["hayır|ayrılamaz", "1 yıl|bir yıl"])
    assert contains_all("İZİN 14 gün", ["izin"])  # Türkçe büyük İ
    assert not contains_all("Salı günü", ["salı", "perşembe"])


def test_answerable_passes_with_content_and_valid_citation():
    s = score_answer(q("dogrudan", ["75"], expected_chunk=3), "75 Euro'dur [1].", CHUNKS, MARKERS)
    assert s.passed and s.content_ok
    assert s.retrieval_rank == 1
    assert s.cited_expected_chunk is True


def test_answerable_flags_missing_content():
    s = score_answer(q("dogrudan", ["75"]), "50 Euro [1]", CHUNKS, MARKERS)
    assert not s.passed and s.reason == "beklenen bilgi yok"


@pytest.mark.parametrize("answer, invalid", [("75 [K1]", ["K1"]), ("75 [7]", ["7"])])
def test_answerable_flags_invalid_citation(answer, invalid):
    s = score_answer(q("dogrudan", ["75"]), answer, CHUNKS, MARKERS)
    assert not s.passed and s.invalid_citations == invalid


def test_answerable_requires_citation():
    s = score_answer(q("dogrudan", ["75"]), "75 Euro", CHUNKS, MARKERS)
    assert not s.passed and s.reason == "atıf yok"


def test_wrong_chunk_cited_is_reported_but_not_failed():
    s = score_answer(q("dogrudan", ["75"], expected_chunk=3), "75 [2]", CHUNKS, MARKERS)
    assert s.passed
    assert s.cited_expected_chunk is False


def test_expected_chunk_not_retrieved():
    s = score_answer(q("dogrudan", ["75"], expected_chunk=0), "75 [1]", CHUNKS, MARKERS)
    assert s.retrieval_rank is None and s.cited_expected_chunk is None


@pytest.mark.parametrize("category", ["yok", "alakasiz"])
def test_refusal_categories(category):
    assert score_answer(q(category), "Bu bilgi dokümanlarda yer almıyor.", CHUNKS, MARKERS).passed
    assert score_answer(q(category), "Şirket araba vermiyor.", CHUNKS, MARKERS).reason == "ret etmedi"
    assert score_answer(q(category), "Yer almıyor [1]", CHUNKS, MARKERS).reason == "ret ama atıf var"


def test_smalltalk():
    assert score_answer(q("sohbet"), "Merhaba! Nasıl yardımcı olabilirim?", CHUNKS, MARKERS).passed
    assert score_answer(q("sohbet"), "Merhaba [1]", CHUNKS, MARKERS).reason == "gereksiz atıf"


def test_eval_set_file_is_valid():
    eval_set = load_eval_set("data/eval/questions.yaml")
    ids = [x.id for x in eval_set.questions]
    assert len(ids) == len(set(ids))
    for x in eval_set.questions:
        if x.category in {"dogrudan", "cikarim"}:
            assert x.must_contain and x.expected_chunk is not None, x.id


OFF_TOPIC = ["yardımcı olamıyorum"]


def test_not_found_question_rejected_as_off_topic_fails():
    # Şirket sorusuna "konu dışı" reddi: ret var ama türü yanlış
    answer = "Bu konuda yardımcı olamıyorum; yalnızca şirket dokümanlarıyla ilgili soruları cevaplayabiliyorum."
    s = score_answer(q("yok"), answer, CHUNKS, MARKERS, OFF_TOPIC)
    assert not s.passed and s.reason == "konu dışı sandı"
    # Gerçek konu dışı soruda aynı cevap doğrudur
    assert score_answer(q("alakasiz"), answer, CHUNKS, MARKERS, OFF_TOPIC).passed


def test_format_checks():
    question = EvalQuestion(id="t", category="dogrudan", question="Yıllık izin hakkım kaç gün?", expected="", must_contain=["14"])
    assert score_answer(question, "Yıllık izin hakkım kaç gün? 14 gün [1]", CHUNKS, MARKERS).reason == "soruyu tekrar etti"
    assert score_answer(question, "**14 gün** [1]", CHUNKS, MARKERS).reason == "markdown kullandı"
    assert score_answer(question, "14 gün [1]", CHUNKS, MARKERS).passed

