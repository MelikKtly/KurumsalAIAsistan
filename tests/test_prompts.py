import pytest

from app.prompts import loader
from app.prompts.loader import available_versions, load_prompt


def test_rag_versions_available():
    assert {"v1", "v2"} <= set(available_versions("rag"))


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_rag_prompt_renders_context_and_question(version):
    messages = load_prompt("rag", version).template.format_messages(context="BAĞLAM-METNİ", question="SORU-METNİ")
    assert "BAĞLAM-METNİ" in messages[0].content
    assert messages[1].content == "SORU-METNİ"


def test_v2_embeds_fixed_replies():
    spec = load_prompt("rag", "v2")
    system = spec.template.format_messages(context="", question="")[0].content
    assert spec.fixed_replies["off_topic"] in system
    assert spec.fixed_replies["not_found"] in system
    assert "{" not in system  # doldurulmamış şablon değişkeni kalmamalı


def test_missing_version_lists_available():
    with pytest.raises(FileNotFoundError, match="v1"):
        load_prompt("rag", "v999")


def test_variable_mismatch_is_rejected(tmp_path, monkeypatch):
    (tmp_path / "bozuk").mkdir()
    (tmp_path / "bozuk" / "v1.yaml").write_text(
        "input_variables: [context, question]\n"
        "messages:\n"
        "  - {role: system, content: 'Bağlam: {contxt}'}\n"  # yazım hatası
        "  - {role: human, content: '{question}'}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(loader, "PROMPTS_DIR", tmp_path)
    with pytest.raises(ValueError, match="contxt"):
        load_prompt("bozuk", "v1")
