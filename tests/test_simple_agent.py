from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from app.agent.simple_agent import run_simple_agent
from tests.fakes import ScriptedToolModel, tool_call


# Testte gerçek retrieval / HTTP yerine sabit sonuç dönen sahte araçlar
@tool
def search_documents(query: str) -> str:
    """Sahte doküman araması."""
    return "[1] (el_kitabi.pdf, sayfa 2)\nBabalık izni 10 gündür."


@tool
def get_exchange_rate(base: str, target: str = "TRY") -> str:
    """Sahte kur."""
    return f"1 {base} = 50 {target}"


TOOLS = [search_documents, get_exchange_rate]


def test_answers_directly_without_tools():
    model = ScriptedToolModel([AIMessage(content="Merhaba!")])
    result = run_simple_agent("Merhaba", llm=model, tools=TOOLS)
    assert result.answer == "Merhaba!" and result.steps == [] and result.llm_calls == 1


def test_calls_tool_and_uses_result():
    model = ScriptedToolModel([
        AIMessage(content="", tool_calls=[tool_call("search_documents", {"query": "babalık izni"})]),
        AIMessage(content="Babalık izni 10 gündür [1]."),
    ])
    result = run_simple_agent("Babalık izni?", llm=model, tools=TOOLS)
    assert [s.tool for s in result.steps] == ["search_documents"]
    assert result.steps[0].args == {"query": "babalık izni"}
    assert result.answer == "Babalık izni 10 gündür [1]." and result.llm_calls == 2
    # Araç sonucu ikinci LLM çağrısında modele ToolMessage olarak ulaşmalı
    tool_msgs = [m for m in model.seen[1] if isinstance(m, ToolMessage)]
    assert "10 gündür" in tool_msgs[0].content


def test_multiple_tools_in_one_turn():
    model = ScriptedToolModel([
        AIMessage(content="", tool_calls=[
            tool_call("search_documents", {"query": "harcırah"}, "c1"),
            tool_call("get_exchange_rate", {"base": "EUR"}, "c2"),
        ]),
        AIMessage(content="75 × 50 = 3750 TL"),
    ])
    result = run_simple_agent("Harcırah kaç TL?", llm=model, tools=TOOLS)
    assert [s.tool for s in result.steps] == ["search_documents", "get_exchange_rate"]


def test_unknown_tool_is_reported_not_crashed():
    model = ScriptedToolModel([
        AIMessage(content="", tool_calls=[tool_call("hava_durumu", {})]),
        AIMessage(content="Bu bilgiye ulaşamadım."),
    ])
    result = run_simple_agent("?", llm=model, tools=TOOLS)
    assert result.steps[0].result.startswith("HATA: 'hava_durumu'")


def test_second_round_tool_request_cannot_be_served():
    # Tek adımlı agent'ın sınırı: model 2. turda yeni araç isterse yerine getirilemez
    model = ScriptedToolModel([
        AIMessage(content="", tool_calls=[tool_call("search_documents", {"query": "harcırah"})]),
        AIMessage(content="", tool_calls=[tool_call("get_exchange_rate", {"base": "EUR"})]),
    ])
    result = run_simple_agent("Harcırah kaç TL?", llm=model, tools=TOOLS)
    assert "birden fazla araç turu" in result.answer
