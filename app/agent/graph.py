"""LangGraph ile çok adımlı agent — Faz 3.4–3.6, 3.8.

Durum makinesi (state machine):

    START → agent ──(araç istedi)──→ tools ──→ agent   (döngü: sonuçları değerlendirip devam/bitir)
              ├────(araç istemedi)──→ END
              └────(adım limiti)────→ finalize → END

- agent:    LLM araç listesiyle çağrılır; ya araç ister ya da son cevabı yazar ("planla").
- tools:    İstenen araçlar çalıştırılır, sonuçlar mesaj geçmişine eklenir ("araç çağır").
- agent'a geri dönülür: model sonuçları görüp yeni araç ister ya da bitirir ("değerlendir").
- finalize: Adım limiti dolunca araçsız son bir cevap üretilir (sonsuz döngü koruması).

Tek adımlı agent'tan (simple_agent.py) farkı: araç turu sayısı sabit değil; model bir aracın
sonucunu gördükten sonra ikinci bir araca ihtiyaç duyarsa onu da çağırabilir.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agent.simple_agent import OUTPUT_LIMIT_ANSWER, AgentResult, ToolStep, hit_output_limit, run_tool_calls
from app.agent.tools import TOOLS
from app.config import get_settings
from app.llm import get_agent_llm
from app.observability import TokenUsage, append_request_log, timer
from app.prompts.loader import load_prompt


# --- Durum (state) ---
# Graf boyunca taşınan veri. Her düğüm bir sözlük döndürür; LangGraph bunu state'e uygular.
# Annotated[..., reducer]: düğümün döndürdüğü değerin mevcut değerle NASIL birleşeceği.
#   add_messages → yeni mesajları listeye ekler (üzerine yazmaz)
#   operator.add → listeleri uç uca ekler / sayıları ve TokenUsage'ları toplar
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    steps: Annotated[list[ToolStep], operator.add]
    trace: Annotated[list[dict], operator.add]
    llm_calls: Annotated[int, operator.add]
    tokens: Annotated[TokenUsage, operator.add]
    stop_reason: str


FINALIZE_INSTRUCTION = (
    "Adım limitine ulaşıldı; artık araç kullanamazsın. Şu ana kadar topladığın bilgilerle "
    "soruyu cevapla ve eksik kalan kısmı açıkça belirt. Bilgi uydurma."
)


def build_agent_graph(llm: BaseChatModel, tools: list[BaseTool], max_steps: int):
    """Grafı kurar ve derler. llm ve tools dışarıdan verilir (testlerde sahteleri)."""
    model_with_tools = llm.bind_tools(tools)

    def agent_node(state: AgentState) -> dict:
        """Planla / değerlendir: model ya araç ister ya da son cevabı yazar."""
        with timer() as t:
            message = model_with_tools.invoke(state["messages"])
        usage = TokenUsage.from_message(message)
        event = {
            "node": "agent",
            "llm_call": state["llm_calls"] + 1,
            "planned_tools": [{"tool": c["name"], "args": c["args"]} for c in message.tool_calls],
            "content": message.content[:300],
            "ms": t["ms"],
            "tokens": usage.total_tokens,
        }
        update = {"messages": [message], "llm_calls": 1, "tokens": usage, "trace": [event]}
        if hit_output_limit(message):
            # Cevap kesildi: boş cevap yerine açık bir mesajla dur (route_after_agent → END)
            event["output_limit"] = True
            update["messages"] = [message.model_copy(update={"content": OUTPUT_LIMIT_ANSWER})]
            update["stop_reason"] = "output_limit"
        return update

    def tools_node(state: AgentState) -> dict:
        """Araç çağır: son AI mesajındaki tüm araç isteklerini çalıştırır."""
        tool_messages, steps = run_tool_calls(state["messages"][-1], tools)
        events = [{"node": "tools", **s.model_dump()} for s in steps]
        return {"messages": tool_messages, "steps": steps, "trace": events}

    def finalize_node(state: AgentState) -> dict:
        """Adım limiti dolduğunda araçsız son cevap (llm araçlara bağlanmamış haliyle çağrılır)."""
        messages = state["messages"]
        # Son AI mesajı yerine getirilmemiş araç istekleri içeriyor; modele bunu dürüstçe söyle
        with timer() as t:
            message = llm.invoke([*messages[:-1], HumanMessage(content=FINALIZE_INSTRUCTION)])
        usage = TokenUsage.from_message(message)
        event = {"node": "finalize", "content": message.content[:300], "ms": t["ms"], "tokens": usage.total_tokens}
        return {"messages": [message], "llm_calls": 1, "tokens": usage, "trace": [event], "stop_reason": "max_steps"}

    def route_after_agent(state: AgentState) -> str:
        """Koşullu kenar: agent'tan sonra nereye gidilecek?"""
        last = state["messages"][-1]
        if not last.tool_calls:
            return END  # Model araç istemedi → cevap hazır
        if state["llm_calls"] >= max_steps:
            return "finalize"  # Daha fazla tur yok → limit koruması
        return "tools"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, ["tools", "finalize", END])
    graph.add_edge("tools", "agent")  # Döngü: araç sonuçları → tekrar değerlendirme
    graph.add_edge("finalize", END)
    return graph.compile()


def run_graph_agent(
    question: str,
    llm: BaseChatModel | None = None,
    tools: list[BaseTool] | None = None,
    max_steps: int | None = None,
    prompt_version: str | None = None,  # None → .env'deki AGENT_PROMPT_VERSION
) -> AgentResult:
    settings = get_settings()
    max_steps = max_steps or settings.agent_max_steps
    graph = build_agent_graph(llm or get_agent_llm(), tools if tools is not None else TOOLS, max_steps)
    initial: AgentState = {
        "messages": load_prompt("agent", prompt_version or settings.agent_prompt_version).template.format_messages(
            question=question
        ),
        "steps": [],
        "trace": [],
        "llm_calls": 0,
        "tokens": TokenUsage(),
        "stop_reason": "done",
    }
    with timer() as t:
        # recursion_limit: LangGraph'ın kendi güvenlik sınırı (düğüm geçişi sayısı). Bizim
        # max_steps kontrolümüz önce devreye girer; bu ikinci bir emniyet kemeri.
        final = graph.invoke(initial, config={"recursion_limit": max_steps * 3 + 5})

    result = AgentResult(
        question=question,
        answer=final["messages"][-1].content.strip(),
        steps=final["steps"],
        llm_calls=final["llm_calls"],
        tokens=final["tokens"],
        total_ms=t["ms"],
        trace=final["trace"],
        stop_reason=final["stop_reason"],
    )
    # Adım adım iz dosyaya: hangi araç hangi girdiyle çağrıldı, ne döndü, ne kadar sürdü (debug + eval)
    append_request_log({"agent": "graph", **result.model_dump()}, settings.agent_log_path)
    return result
