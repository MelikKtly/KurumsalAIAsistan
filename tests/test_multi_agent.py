from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from app.agent.multi_agent import run_multi_agent
from tests.fakes import ScriptedStructuredModel, ScriptedToolModel, tool_call


@tool
def search_documents(query: str) -> str:
    """Sahte doküman araması."""
    return "[1] Yurt dışı yemek harcırahı 75 Euro'dur."


@tool
def get_exchange_rate(base: str, target: str = "TRY") -> str:
    """Sahte kur."""
    return f"1 {base} = 50 {target}"


TOOLS = [search_documents, get_exchange_rate]


def decision(action: str, instruction: str = "", final_answer: str = "") -> dict:
    return {"thought": "...", "action": action, "instruction": instruction, "final_answer": final_answer}


def test_supervisor_delegates_twice_then_finishes():
    supervisor = ScriptedStructuredModel([
        decision("delegate", instruction="Dokümanda yurt dışı harcırahı bul"),
        decision("delegate", instruction="EUR/TRY kurunu al"),
        decision("finish", final_answer="75 EUR × 50 = 3.750 TL [1]"),
    ])
    worker = ScriptedToolModel([
        AIMessage(content="", tool_calls=[tool_call("search_documents", {"query": "harcırah"})]),
        AIMessage(content="75 Euro [1]"),
        AIMessage(content="", tool_calls=[tool_call("get_exchange_rate", {"base": "EUR"})]),
        AIMessage(content="1 EUR = 50 TRY"),
    ])
    result = run_multi_agent("Harcırah kaç TL?", supervisor_llm=supervisor, worker_llm=worker, tools=TOOLS)
    assert result.answer == "75 EUR × 50 = 3.750 TL [1]"
    assert [s.tool for s in result.steps] == ["search_documents", "get_exchange_rate"]
    assert [e["node"] for e in result.trace] == ["supervisor", "worker", "supervisor", "worker", "supervisor"]
    assert result.llm_calls == 3 + 4  # 3 supervisor kararı + worker'ın 4 LLM çağrısı


def test_supervisor_finishes_directly_for_smalltalk():
    supervisor = ScriptedStructuredModel([decision("finish", final_answer="Merhaba!")])
    result = run_multi_agent("Merhaba", supervisor_llm=supervisor, worker_llm=ScriptedToolModel([]), tools=TOOLS)
    assert result.answer == "Merhaba!" and result.steps == []


def test_round_limit_stops_endless_delegation():
    # Hep görev vermek isteyen supervisor: tur limitinde eldeki son sonuçla bitmeli
    supervisor = ScriptedStructuredModel([decision("delegate", instruction="kur al")] * 2)
    worker = ScriptedToolModel([AIMessage(content="1 EUR = 50 TRY")])
    result = run_multi_agent("?", supervisor_llm=supervisor, worker_llm=worker, tools=TOOLS, max_rounds=2)
    assert result.stop_reason == "max_steps" and result.answer == "1 EUR = 50 TRY"


def test_invalid_supervisor_output_finishes_safely():
    result = run_multi_agent("?", supervisor_llm=ScriptedStructuredModel([None]), worker_llm=ScriptedToolModel([]), tools=TOOLS)
    assert result.answer == "Cevap üretilemedi."
