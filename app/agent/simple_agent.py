"""Tek adımlı (döngüsüz) araç kullanan agent — Faz 3.2/3.3.

Akış:
  1. Model, soruyu ve araç listesini görür; araç çağırmaya karar verebilir (tool_calls).
  2. Kodumuz istenen araçları çalıştırır, sonuçları modele geri verir (ToolMessage).
  3. Model sonuçlarla son cevabı yazar.

"Tek adımlı": en fazla bir araç turu vardır. Model ikinci turda yeni bir araca ihtiyaç
duysa bile çağıramaz — bu sınırlama Faz 3.4'teki LangGraph döngüsüyle kalkıyor.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.agent.tools import TOOLS
from app.config import get_settings
from app.llm import get_agent_llm
from app.observability import TokenUsage, timer
from app.prompts.loader import load_prompt


class ToolStep(BaseModel):
    """Agent'ın attığı bir araç adımı (loglama ve inceleme için)."""

    tool: str
    args: dict
    result: str  # Aracın döndürdüğü metin (uzunsa kısaltılmış)
    ms: float


class AgentResult(BaseModel):
    """Tüm agent türlerinin (tek adımlı, LangGraph, multi-agent) ortak sonuç yapısı."""

    question: str
    answer: str
    steps: list[ToolStep]  # Hangi araç, hangi argümanla, ne döndü — sırasıyla
    llm_calls: int
    tokens: TokenUsage
    total_ms: float
    # Adım adım iz (LangGraph agent'ı doldurur): LLM kararları + araç çalışmaları
    trace: list[dict] = []
    # Neden durdu: "done" | "max_steps" (adım limiti) | "output_limit" (token sınırı)
    stop_reason: str = "done"


# Model token sınırına takılınca (düşünme bitmeden kesilince) kullanıcıya gösterilecek mesaj
OUTPUT_LIMIT_ANSWER = "Model bu soru için cevap üretirken çıktı sınırına ulaştı; lütfen soruyu daha basit sorun."


def hit_output_limit(message: AIMessage) -> bool:
    """Model token sınırına takılıp araç çağrısı ya da cevap üretemeden kesildi mi?

    Ollama, num_predict sınırına ulaşınca done_reason="length" döner. Düşünme modunda
    kesilme genelde düşünce sırasında olur → içerik boş, araç çağrısı yok.
    """
    return message.response_metadata.get("done_reason") == "length" and not message.tool_calls


def run_tool_calls(message: AIMessage, tools: list[BaseTool]) -> tuple[list[ToolMessage], list[ToolStep]]:
    """Modelin istediği araç çağrılarını çalıştırır.

    Dönüş: modele geri verilecek ToolMessage'lar + loglama için adımlar.
    """
    by_name = {t.name: t for t in tools}
    tool_messages, steps = [], []
    for call in message.tool_calls:  # Model bir mesajda birden fazla araç isteyebilir
        with timer() as t:
            tool = by_name.get(call["name"])
            if tool is None:
                # Model olmayan bir araç uydurursa çökme yok: hatayı modele bildir
                result = f"HATA: '{call['name']}' adında bir araç yok. Mevcut araçlar: {list(by_name)}"
            else:
                result = str(tool.invoke(call["args"]))
        # tool_call_id: sonucun hangi çağrıya ait olduğunu modele söyler (birden fazla çağrıda şart)
        tool_messages.append(ToolMessage(content=result, tool_call_id=call["id"], name=call["name"]))
        steps.append(ToolStep(tool=call["name"], args=call["args"], result=result[:500], ms=t["ms"]))
    return tool_messages, steps


def run_simple_agent(
    question: str,
    llm: BaseChatModel | None = None,
    tools: list[BaseTool] | None = None,
    prompt_version: str | None = None,  # None → .env'deki AGENT_PROMPT_VERSION
) -> AgentResult:
    tools = tools if tools is not None else TOOLS
    # bind_tools: araçların JSON şemalarını modele iletir; model artık tool_call üretebilir
    model = (llm or get_agent_llm()).bind_tools(tools)
    prompt = load_prompt("agent", prompt_version or get_settings().agent_prompt_version)
    messages: list[BaseMessage] = prompt.template.format_messages(question=question)
    tokens = TokenUsage()
    steps: list[ToolStep] = []

    with timer() as total_t:
        # 1) Karar: araç mı çağıracak, doğrudan mı cevaplayacak?
        first = model.invoke(messages)
        tokens += TokenUsage.from_message(first)
        llm_calls = 1
        answer = OUTPUT_LIMIT_ANSWER if hit_output_limit(first) else first.content

        if first.tool_calls:
            # 2) Araçları çalıştır, 3) sonuçlarla son cevabı üret
            tool_messages, steps = run_tool_calls(first, tools)
            messages += [first, *tool_messages]  # Konuşma geçmişi: istek → araç sonuçları
            final = model.invoke(messages)
            tokens += TokenUsage.from_message(final)
            llm_calls += 1
            answer = final.content
            # Model ikinci turda da araç isterse tek adımlı agent bunu yerine getiremez
            if final.tool_calls and not answer:
                answer = "Bu soru için birden fazla araç turu gerekiyor; tek adımlı agent cevaplayamadı."

    return AgentResult(
        question=question,
        answer=answer.strip(),
        steps=steps,
        llm_calls=llm_calls,
        tokens=tokens,
        total_ms=total_t["ms"],
    )
