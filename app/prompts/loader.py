from functools import lru_cache
from pathlib import Path

import yaml
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

PROMPTS_DIR = Path(__file__).parent


class PromptSpec(BaseModel):
    """Bir prompt dosyasının (app/prompts/<ad>/<versiyon>.yaml) içeriği."""

    name: str
    version: str
    description: str = ""
    input_variables: list[str]
    fixed_replies: dict[str, str] = {}
    template: ChatPromptTemplate


def available_versions(name: str) -> list[str]:
    return sorted(p.stem for p in (PROMPTS_DIR / name).glob("*.yaml"))


@lru_cache
def load_prompt(name: str, version: str) -> PromptSpec:
    """Prompt dosyasını okuyup ChatPromptTemplate'e çevirir.

    `fixed_replies` metinleri şablona sabit olarak gömülür (partial). Şablonda kalan
    değişkenler `input_variables` ile birebir eşleşmezse hata verir; böylece
    dosyada unutulan/yanlış yazılan bir {değişken} sessizce bozuk prompta dönüşmez.
    """
    path = PROMPTS_DIR / name / f"{version}.yaml"
    if not path.is_file():
        raise FileNotFoundError(
            f"Prompt bulunamadı: {path} (mevcut versiyonlar: {available_versions(name)})"
        )

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fixed_replies = data.get("fixed_replies", {})
    template = ChatPromptTemplate.from_messages(
        [(m["role"], m["content"]) for m in data["messages"]]
    ).partial(**fixed_replies)

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
