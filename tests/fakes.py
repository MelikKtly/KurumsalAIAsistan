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
