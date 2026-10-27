from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

import app.retrieval.rag as rag
from app.ingestion.pipeline import ingest_pdf
from app.observability import TokenUsage
from app.retrieval.groundedness import GroundednessVerdict, GroundingResult, check_groundedness
from app.vectorstore import get_vector_store

DOCS = [Document(page_content="Yurt dışı harcırah 75 Euro.", metadata={"source": "a.pdf", "page": 0})]


class FakeJudge:
    """Gerçek LLM yerine geçen sahte hakem.

    check_groundedness `llm.with_structured_output(Şema, include_raw=True)` çağırır; gerçek
    model {"raw": AIMessage, "parsed": Şema | None, "parsing_error": ...} döndürür. Burada
    aynı yapı sabit değerlerle üretilir. `invalid=True` modelin şemaya uymayan çıktı
    ürettiği durumu, `error` bağlantı hatası gibi exception'ları taklit eder.
    """

    def __init__(self, unsupported=(), invalid: bool = False, error: Exception | None = None):
        self.unsupported = list(unsupported)
        self.invalid = invalid
        self.error = error

    def with_structured_output(self, schema, include_raw: bool = False):
        def run(_prompt_value):
            if self.error:
                raise self.error
            # Ham mesajda token bilgisi: hakem çağrısının kullanımı ölçülebilsin
            raw = AIMessage(content="{}", usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120})
            if self.invalid:
                return {"raw": raw, "parsed": None, "parsing_error": ValueError("bozuk JSON")}
            parsed = schema(claims_check="kontrol edildi", unsupported_claims=self.unsupported)
            return {"raw": raw, "parsed": parsed, "parsing_error": None}

        return RunnableLambda(run)


def test_no_unsupported_claims_means_grounded():
    result = check_groundedness("?", "75 Euro [1]", DOCS, llm=FakeJudge())
    assert result.verdict.grounded is True and result.verdict.unsupported_claims == []
    # Hakem çağrısının token kullanımı ham mesajdan okunur
    assert (result.usage.input_tokens, result.usage.output_tokens, result.usage.total_tokens) == (100, 20, 120)


def test_any_unsupported_claim_means_not_grounded():
    # Karar modelden değil koddan gelir: tek bir desteksiz iddia yeterli
    verdict = check_groundedness("?", "100 Euro [1]", DOCS, llm=FakeJudge(["100 Euro"])).verdict
    assert verdict.grounded is False and verdict.unsupported_claims == ["100 Euro"]


def test_invalid_judge_output_returns_none():
    # Şemaya uymayan çıktı → kontrol yapılamadı (verdict None), cevap engellenmez; token yine sayılır
    result = check_groundedness("?", "75 Euro", DOCS, llm=FakeJudge(invalid=True))
    assert result.verdict is None and result.usage.total_tokens == 120


def test_connection_errors_are_not_swallowed():
    # Ollama kapalıysa hata yutulmamalı (API'nin 503 dönebilmesi için)
    with pytest.raises(ConnectionError):
        check_groundedness("?", "75 Euro", DOCS, llm=FakeJudge(error=ConnectionError()))


# --- answer_question entegrasyonu: hakem ne zaman çalışmalı? ---
@pytest.fixture
def store(tmp_path):
    store = get_vector_store(embeddings=DeterministicFakeEmbedding(size=64), persist_directory=str(tmp_path / "c"))
    ingest_pdf(Path("data/samples/ornek_ik_el_kitabi.pdf"), store)
    return store


@pytest.fixture
def judge_calls(monkeypatch):
    """Hakemi sahtesiyle değiştirir ve kaç kez çağrıldığını kaydeder."""
    calls = []

    def fake_check(question, answer, documents, llm=None):
        calls.append(answer)
        verdict = GroundednessVerdict(claims_check="", unsupported_claims=[], grounded=True)
        return GroundingResult(verdict=verdict, usage=TokenUsage(input_tokens=100, output_tokens=20))

    monkeypatch.setattr(rag, "check_groundedness", fake_check)
    return calls


def fake_llm(reply: str) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([AIMessage(content=reply)]))


def test_judge_runs_for_answered_when_enabled(store, judge_calls):
    result = rag.answer_question("izin", llm=fake_llm("14 gün [1]"), vector_store=store, check_grounding=True)
    assert judge_calls == ["14 gün [1]"]
    assert result.groundedness.grounded is True
    # Hakem süresi ve token'ı metriklere yansımalı
    assert result.metrics.grounding_ms is not None
    assert result.metrics.grounding_tokens.total_tokens == 120


def test_judge_skipped_for_not_found(store, judge_calls):
    not_found = rag.get_rag_prompt().fixed_replies["not_found"]
    result = rag.answer_question("CEO?", llm=fake_llm(not_found), vector_store=store, check_grounding=True)
    # "Bilgi yok" cevabında doğrulanacak iddia yok → hakem çağrılmaz
    assert judge_calls == [] and result.groundedness is None


def test_judge_skipped_when_disabled(store, judge_calls):
    result = rag.answer_question("izin", llm=fake_llm("14 gün [1]"), vector_store=store, check_grounding=False)
    assert judge_calls == [] and result.groundedness is None
