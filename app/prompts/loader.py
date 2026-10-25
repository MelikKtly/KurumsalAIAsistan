"""Versiyonlu prompt dosyalarını (app/prompts/<ad>/<versiyon>.yaml) yükler.

Promptlar koda gömülmez: düzenlemek için YAML dosyasını değiştirmek, yeni bir
deneme için yeni bir versiyon dosyası (v3.yaml) eklemek yeterlidir. Hangi
versiyonun kullanılacağı .env'deki RAG_PROMPT_VERSION ile seçilir.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

# Bu dosyanın bulunduğu klasör (app/prompts/). Prompt dosyaları bunun altında aranır.
PROMPTS_DIR = Path(__file__).parent


class PromptSpec(BaseModel):
    """Bir prompt dosyasının (app/prompts/<ad>/<versiyon>.yaml) içeriği."""

    name: str  # örn. "rag" (klasör adı)
    version: str  # örn. "v2" (dosya adı)
    description: str = ""  # Versiyonun ne değiştirdiği (raporlarda gösterilir)
    input_variables: list[str]  # Çalışırken doldurulacak değişkenler, örn. [context, question]
    fixed_replies: dict[str, str] = {}  # Prompta gömülen sabit cevap kalıpları
    template: ChatPromptTemplate  # LangChain'in kullanıma hazır şablonu


def available_versions(name: str) -> list[str]:
    """Bir prompt için mevcut versiyonlar, örn. ["v1", "v2"]."""
    # p.stem: uzantısız dosya adı ("v1.yaml" → "v1")
    return sorted(p.stem for p in (PROMPTS_DIR / name).glob("*.yaml"))


# Aynı versiyon her istekte diskten tekrar okunmasın diye sonuç cache'lenir.
# (Not: bu yüzden YAML değiştirildiğinde değişikliğin görülmesi için uygulama yeniden başlatılmalı.)
@lru_cache
def load_prompt(name: str, version: str) -> PromptSpec:
    """Prompt dosyasını okuyup ChatPromptTemplate'e çevirir.

    `fixed_replies` metinleri şablona sabit olarak gömülür (partial). Şablonda kalan
    değişkenler `input_variables` ile birebir eşleşmezse hata verir; böylece
    dosyada unutulan/yanlış yazılan bir {değişken} sessizce bozuk prompta dönüşmez.
    """
    path = PROMPTS_DIR / name / f"{version}.yaml"
    if not path.is_file():
        # Yanlış versiyon adı yazıldığında hangi seçeneklerin olduğunu göster
        raise FileNotFoundError(
            f"Prompt bulunamadı: {path} (mevcut versiyonlar: {available_versions(name)})"
        )

    # safe_load: YAML içinde Python nesnesi oluşturan etiketleri çalıştırmaz (güvenli okuma)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fixed_replies = data.get("fixed_replies", {})
    # YAML'daki mesaj listesi ([{role: system, content: ...}, {role: human, ...}])
    # → LangChain'in beklediği (rol, metin) çiftleri → ChatPromptTemplate.
    # .partial(...): şablondaki {off_topic}, {not_found} gibi değişkenleri şimdiden doldurur;
    # geriye sadece her istekte değişenler ({context}, {question}) kalır.
    template = ChatPromptTemplate.from_messages(
        [(m["role"], m["content"]) for m in data["messages"]]
    ).partial(**fixed_replies)

    # Doğrulama: şablonda kalan değişkenler dosyada beyan edilenlerle aynı olmalı.
    # Örn. "{contxt}" yazım hatası burada yakalanır; yoksa model bağlamsız çalışırdı.
    expected = set(data["input_variables"])
    if set(template.input_variables) != expected:
        raise ValueError(
            f"{path.name}: şablon değişkenleri {sorted(template.input_variables)}, "
            f"beklenen {sorted(expected)}"
        )

    return PromptSpec(
        name=name,
        version=version,
        description=data.get("description", "").strip(),
        input_variables=data["input_variables"],
        fixed_replies=fixed_replies,
        template=template,
    )
