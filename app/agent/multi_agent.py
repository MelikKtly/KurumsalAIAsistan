"""Supervisor + tek worker multi-agent — Faz 3.7.

    START → supervisor ──(delegate)──→ worker ──→ supervisor   (döngü)
                 └──────(finish)──────→ END

- supervisor: Araç kullanmaz. Soruyu alt görevlere böler, worker'a talimat verir, sonuçları
  değerlendirir ve son cevabı yazar. Kararını yapılandırılmış çıktıyla (SupervisorDecision) verir.
- worker:     Faz 3.4'teki LangGraph agent'ı (araçlı). Supervisor'ın verdiği alt görevi çözer.

Tek-agent'la karşılaştırma için scripts/eval_agent.py --agent multi kullanılır.
"""

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agent.graph import run_graph_agent
from app.agent.simple_agent import AgentResult, ToolStep
from app.config import get_settings
from app.llm import get_llm
from app.observability import TokenUsage, append_request_log, timer
from app.prompts.loader import load_prompt


# Alan sırası bilinçli: önce düşünce, sonra karar (groundedness hakeminden öğrenilen ders —
# LLM JSON alanlarını sırayla üretir; karar önce gelirse düşünmeden verilir).
class SupervisorDecision(BaseModel):
    thought: str = Field(description="Ne biliniyor, cevap için ne eksik — kısa değerlendirme")
    action: Literal["delegate", "finish"] = Field(description="delegate: worker'a görev ver; finish: cevabı yaz")
    instruction: str = Field(description="action=delegate ise worker için tek ve net görev, değilse boş")
    final_answer: str = Field(description="action=finish ise kullanıcıya son cevap, değilse boş")


class MultiAgentState(TypedDict):
    question: str
    worker_results: Annotated[list[dict], operator.add]  # [{instruction, answer}]
    steps: Annotated[list[ToolStep], operator.add]
    trace: Annotated[list[dict], operator.add]
    llm_calls: Annotated[int, operator.add]
    tokens: Annotated[TokenUsage, operator.add]
    pending_instruction: str
    final_answer: str
    rounds: Annotated[int, operator.add]  # Supervisor kaç kez karar verdi


def format_history(results: list[dict]) -> str:
    if not results:
        return "(henüz yok)"
    return "\n\n".join(f"Görev {i}: {r['instruction']}\nSonuç: {r['answer']}" for i, r in enumerate(results, 1))


def build_multi_agent_graph(
    supervisor_llm: BaseChatModel,
    worker_llm: BaseChatModel | None,
    tools: list[BaseTool] | None,
    max_rounds: int,
):
    # include_raw=True: token sayısı için ham mesaj da gelsin (groundedness'taki gibi)
    decide = load_prompt("supervisor", "v2").template | supervisor_llm.with_structured_output(
        SupervisorDecision, include_raw=True
    )

    def supervisor_node(state: MultiAgentState) -> dict:
        with timer() as t:
            out = decide.invoke({"question": state["question"], "history": format_history(state["worker_results"])})
        usage = TokenUsage.from_message(out["raw"])
        decision: SupervisorDecision | None = out["parsed"]
        rounds = state["rounds"] + 1
        if decision is None:
            # Şemaya uymayan çıktı: güvenli şekilde bitir, eldeki son worker sonucunu ver
            last = state["worker_results"][-1]["answer"] if state["worker_results"] else ""
            decision = SupervisorDecision(thought="(geçersiz karar çıktısı)", action="finish",
                                          instruction="", final_answer=last or "Cevap üretilemedi.")
        elif decision.action == "delegate" and rounds >= max_rounds:
            # Tur limiti: yeni görev verilemez, eldeki sonuçlarla bitir
            last = state["worker_results"][-1]["answer"] if state["worker_results"] else "Cevap üretilemedi."
            decision = decision.model_copy(update={"action": "finish", "final_answer": last})
        event = {"node": "supervisor", "round": rounds, "thought": decision.thought[:300],
                 "action": decision.action, "instruction": decision.instruction, "ms": t["ms"],
                 "tokens": usage.total_tokens}
        return {
            "llm_calls": 1, "tokens": usage, "trace": [event], "rounds": 1,
            "pending_instruction": decision.instruction if decision.action == "delegate" else "",
            "final_answer": decision.final_answer if decision.action == "finish" else "",
        }

    def worker_node(state: MultiAgentState) -> dict:
        # Worker, supervisor'ın talimatını kendi sorusu gibi alıp araçlarla çözer
        result = run_graph_agent(state["pending_instruction"], llm=worker_llm, tools=tools)
        event = {"node": "worker", "instruction": state["pending_instruction"], "answer": result.answer[:300],
                 "tools": [s.tool for s in result.steps], "ms": result.total_ms, "tokens": result.tokens.total_tokens}
        return {
            "worker_results": [{"instruction": state["pending_instruction"], "answer": result.answer}],
            "steps": result.steps, "trace": [event], "llm_calls": result.llm_calls, "tokens": result.tokens,
        }

    def route(state: MultiAgentState) -> str:
        return "worker" if state["pending_instruction"] else END

    graph = StateGraph(MultiAgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("worker", worker_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route, ["worker", END])
    graph.add_edge("worker", "supervisor")
    return graph.compile()


def run_multi_agent(
    question: str,
    supervisor_llm: BaseChatModel | None = None,
    worker_llm: BaseChatModel | None = None,
    tools: list[BaseTool] | None = None,
    max_rounds: int = 4,
    prompt_version: str | None = None,  # eval_agent.py arayüzüyle uyum için (worker .env'dekini kullanır)
) -> AgentResult:
    # Supervisor düşünmesiz hızlı LLM (araç çağırmıyor, sadece yapılandırılmış karar); worker araçlı agent LLM'i
    graph = build_multi_agent_graph(supervisor_llm or get_llm(), worker_llm, tools, max_rounds)
    initial: MultiAgentState = {
        "question": question, "worker_results": [], "steps": [], "trace": [], "llm_calls": 0,
        "tokens": TokenUsage(), "pending_instruction": "", "final_answer": "", "rounds": 0,
    }
    with timer() as t:
        final = graph.invoke(initial, config={"recursion_limit": max_rounds * 2 + 5})
    result = AgentResult(
        question=question, answer=final["final_answer"].strip(), steps=final["steps"],
        llm_calls=final["llm_calls"], tokens=final["tokens"], total_ms=t["ms"], trace=final["trace"],
        stop_reason="max_steps" if final["rounds"] >= max_rounds else "done",
    )
    append_request_log({"agent": "multi", **result.model_dump()}, get_settings().agent_log_path)
    return result
