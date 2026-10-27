import json

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from app.agent.graph import run_graph_agent
from app.config import get_settings
from tests.fakes import ScriptedToolModel, tool_call


@tool
def search_documents(query: str) -> str:
    """Sahte doküman araması."""
    return "[1] Yurt dışı yemek harcırahı 75 Euro'dur."


@tool
def get_exchange_rate(base: str, target: str = "TRY") -> str:
    """Sahte kur."""
    return f"1 {base} = 50 {target}"


TOOLS = [search_documents, get_exchange_rate]


def test_multi_step_task_uses_both_tools_in_sequence():
    # Tek adımlı agent'ın başaramadığı senaryo: doküman → sonucu gör → kur → cevap
    model = ScriptedToolModel([
        AIMessage(content="", tool_calls=[tool_call("search_documents", {"query": "harcırah"}, "c1")]),
        AIMessage(content="", tool_calls=[tool_call("get_exchange_rate", {"base": "EUR"}, "c2")]),
        AIMessage(content="75 EUR × 50 = 3.750 TL [1]"),
    ])
    result = run_graph_agent("Harcırah kaç TL?", llm=model, tools=TOOLS)
    assert [s.tool for s in result.steps] == ["search_documents", "get_exchange_rate"]
    assert result.answer == "75 EUR × 50 = 3.750 TL [1]"
    assert result.llm_calls == 3 and result.stop_reason == "done"
    # İz: agent → tools → agent → tools → agent
    assert [e["node"] for e in result.trace] == ["agent", "tools", "agent", "tools", "agent"]


def test_direct_answer_without_tools():
    result = run_graph_agent("Merhaba", llm=ScriptedToolModel([AIMessage(content="Merhaba!")]), tools=TOOLS)
    assert result.answer == "Merhaba!" and result.steps == [] and result.llm_calls == 1


def test_max_steps_stops_looping_agent():
    # Hep araç isteyen (döngüye giren) model: limit dolunca finalize ile durmalı
    looping = [AIMessage(content="", tool_calls=[tool_call("search_documents", {"query": "x"}, f"c{i}")]) for i in range(3)]
    model = ScriptedToolModel([*looping, AIMessage(content="Eldeki bilgi: 75 Euro. Kur alınamadı.")])
    result = run_graph_agent("?", llm=model, tools=TOOLS, max_steps=3)
    assert result.stop_reason == "max_steps"
    assert result.llm_calls == 4  # 3 agent çağrısı + 1 finalize
    assert len(result.steps) == 2  # 3. araç isteği limit yüzünden çalıştırılmadı
    assert result.trace[-1]["node"] == "finalize"


def test_run_is_logged_step_by_step():
    model = ScriptedToolModel([
        AIMessage(content="", tool_calls=[tool_call("get_exchange_rate", {"base": "USD"})]),
        AIMessage(content="1 USD = 50 TL"),
    ])
    run_graph_agent("Dolar kaç TL?", llm=model, tools=TOOLS)
    record = json.loads(open(get_settings().agent_log_path, encoding="utf-8").read().splitlines()[-1])
    assert record["agent"] == "graph" and record["steps"][0]["tool"] == "get_exchange_rate"
    assert record["steps"][0]["args"] == {"base": "USD"}


def test_output_limit_stops_with_clear_message():
    # Düşünme döngüsü token sınırına takıldı: içerik boş, araç çağrısı yok, done_reason="length"
    cut = AIMessage(content="", response_metadata={"done_reason": "length"})
    result = run_graph_agent("?", llm=ScriptedToolModel([cut]), tools=TOOLS)
    assert result.stop_reason == "output_limit"
    assert "çıktı sınırına ulaştı" in result.answer
    assert result.trace[-1]["output_limit"] is True
