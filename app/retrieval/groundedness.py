"""Groundedness (bağlama dayanma) kontrolü: "LLM-as-judge" yöntemi.

Cevap üretildikten sonra ikinci bir LLM çağrısı hakem gibi davranır: cevabı ve
cevabın üretildiği bağlamı okuyup cevaptaki her bilginin bağlamda geçip
geçmediğine karar verir. Amaç, modelin uydurduğu (halüsinasyon) bilgileri
kullanıcıya ulaşmadan işaretlemek.

Dikkat: hakem de bir LLM'dir ve yanılabilir. Ne kadar güvenilir olduğu
scripts/eval_groundedness.py ile ölçülür.
"""

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from app.llm import get_llm
from app.observability import TokenUsage
from app.prompts.loader import PromptSpec, load_prompt
from app.retrieval.context import format_context


# Hakemin (LLM) doldurduğu yapı. `with_structured_output` bu şemayı modele iletir
# (Ollama'da JSON şeması olarak); model serbest metin yerine bu alanları doldurur.
# Field(description=...) metinleri modele her alanın ne anlama geldiğini anlatır.
#
# Tasarım notları (scripts/eval_groundedness.py ile ölçülerek varıldı):
# 1) Alan sırası önemli: LLM JSON alanlarını şemadaki sırayla yazar. Karar alanı ilk
#    sıradayken model önce karar verip sonra düşünüyordu → 12 uydurmanın 6'sını kaçırdı.
#    Önce iddiaları kontrol etmek, sonra desteksizleri listelemek "önce düşün" sağlar.
# 2) Karar LLM'e bırakılmaz: model desteksiz iddiaları doğru listelediği hâlde
#    grounded=true diyebiliyordu (kendi tespitiyle çelişki). Bu yüzden karar aşağıda
#    kodda deterministik olarak verilir: desteksiz iddia listesi boş mu?
# Alanlar varsayılan değersiz (zorunlu): opsiyonel alanları model atlayabiliyor.
class JudgeOutput(BaseModel):
    claims_check: str = Field(
        description="Cevaptaki her iddiayı tek tek bağlamla karşılaştırdığın kısa Türkçe değerlendirme"
    )
    unsupported_claims: list[str] = Field(
        description="Bağlamda yer almayan veya bağlamla çelişen ifadeler (hepsi destekliyse boş liste)"
    )


class GroundednessVerdict(JudgeOutput):
    """Hakemin çıktısı + koddan türetilen karar (API cevabında bu döner)."""

    grounded: bool  # True: cevaptaki tüm iddialar bağlamda var


def get_groundedness_prompt() -> PromptSpec:
    return load_prompt("groundedness", "v1")


class GroundingResult(BaseModel):
    """check_groundedness'in dönüşü: hakemin kararı + hakem çağrısının token kullanımı."""

    # None: hakem şemaya uygun bir karar üretemedi (kontrol yapılamadı)
    verdict: GroundednessVerdict | None
    usage: TokenUsage


def check_groundedness(
    question: str,
    answer: str,
    documents: list[Document],
    llm: BaseChatModel | None = None,
    prompt: PromptSpec | None = None,
) -> GroundingResult:
    """Cevabın verilen chunk'lara dayanıp dayanmadığını hakem LLM'e sorar.

    Hakemin çıktısı şemaya uymazsa verdict=None döner (kontrol yapılamadı); bu durumda
    cevap engellenmez, sadece doğrulanmamış olarak kalır.
    """
    prompt = prompt or get_groundedness_prompt()
    # Hakeme, cevabı üreten modelin gördüğü bağlamın AYNISI verilir (aynı numaralarla),
    # böylece cevaptaki [n] atıfları da hakem için anlamlı olur.
    # include_raw=True: ayrıştırılmış nesneyle birlikte modelin ham mesajı da döner
    # → {"raw": AIMessage, "parsed": JudgeOutput | None, "parsing_error": Exception | None}.
    # Token sayıları ham mesajda olduğu için buna ihtiyacımız var. Bu modda ayrıştırma
    # hataları exception fırlatmaz, parsing_error alanına yazılır.
    chain = prompt.template | (llm or get_llm()).with_structured_output(JudgeOutput, include_raw=True)
    # Bağlantı hataları (Ollama kapalı) burada yakalanmaz; yukarıya iletilir → API 503 döner.
    result = chain.invoke({"context": format_context(documents), "question": question, "answer": answer})
    usage = TokenUsage.from_message(result["raw"])

    judged = result["parsed"]
    if judged is None:
        # Model geçersiz JSON veya şemaya uymayan bir çıktı üretti → karar yok
        return GroundingResult(verdict=None, usage=usage)
    # Karar: hakem tek bir desteksiz iddia bile bulduysa cevap bağlama dayanmıyor
    verdict = GroundednessVerdict(**judged.model_dump(), grounded=not judged.unsupported_claims)
    return GroundingResult(verdict=verdict, usage=usage)
