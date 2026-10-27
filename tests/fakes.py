"""Testlerde gerçek LLM yerine kullanılan sahte (mock) modeller."""

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda


def tool_call(name: str, args: dict, call_id: str = "c1") -> dict:
    """AIMessage.tool_calls içindeki bir araç çağrısının biçimi."""
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


class ScriptedToolModel:
    """Önceden yazılmış cevapları sırayla döndüren, araç çağırabilen sahte sohbet modeli.

    Örnek senaryo — önce doküman ara, sonra cevap ver:
        ScriptedToolModel([
            AIMessage(content="", tool_calls=[tool_call("search_documents", {"query": "izin"})]),
            AIMessage(content="10 gün [1]"),
        ])
    `seen` her çağrıda modele giden mesajları kaydeder (örn. araç sonucunun modele ulaştığını doğrulamak için).
    """

    def __init__(self, replies: list[AIMessage]):
        self.replies = list(replies)
        self.seen: list[list] = []
        self.bound_tools: list = []

    def bind_tools(self, tools, **kwargs):
        # Gerçek modelde araç şemalarını modele iletir; burada sadece kaydediyoruz
        self.bound_tools = tools
        return self

    def invoke(self, messages, *args, **kwargs):
        self.seen.append(list(messages))
        if not self.replies:
            raise AssertionError("Senaryodaki cevaplar bitti: model beklenenden fazla çağrıldı")
        return self.replies.pop(0)

    # LangGraph / LCEL zincirinde kullanılabilmesi için Runnable arayüzü
    def as_runnable(self):
        return RunnableLambda(self.invoke)


class ScriptedStructuredModel:
    """with_structured_output(..., include_raw=True) kullanan bileşenler için sahte model.

    Her çağrıda sıradaki sözlüğü şemaya doldurup {"raw", "parsed", "parsing_error"} döndürür.
    None verilirse modelin şemaya uymayan çıktı ürettiği durum taklit edilir.
    """

    def __init__(self, outputs: list[dict | None]):
        self.outputs = list(outputs)

    def with_structured_output(self, schema, include_raw: bool = False):
        def run(_prompt_value):
            data = self.outputs.pop(0)
            raw = AIMessage(content="{}", usage_metadata={"input_tokens": 50, "output_tokens": 10, "total_tokens": 60})
            parsed = None if data is None else schema(**data)
            return {"raw": raw, "parsed": parsed, "parsing_error": None if data else ValueError("bozuk")}

        return RunnableLambda(run)
