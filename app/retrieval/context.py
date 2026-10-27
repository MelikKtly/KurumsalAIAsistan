"""LLM'e verilecek bağlam metninin oluşturulması.

Hem cevap üretimi (rag.py) hem de groundedness hakemi (groundedness.py) aynı
numaralı bağlamı kullanır; ikisinin birebir aynı metni görmesi için tek yerde.
"""

from pathlib import Path

from langchain_core.documents import Document


def format_context(documents: list[Document]) -> str:
    """Chunk'ları LLM'in [n] ile atıf yapabileceği numaralı bloklara çevirir."""
    # Üretilen metin örneği:
    #   [1] (ornek_ik_el_kitabi.pdf, sayfa 2)
    #   4. Yıllık İzin ...
    #
    #   [2] (ornek_ik_el_kitabi.pdf, sayfa 1)
    #   ...
    # LLM'e "kaynağı [n] ile belirt" dediğimiz için numaralar buradan geliyor.
    blocks = []
    for i, doc in enumerate(documents, start=1):
        m = doc.metadata
        # page metadata'da 0'dan başlıyor; insanlar için +1
        blocks.append(f"[{i}] ({Path(m['source']).name}, sayfa {m['page'] + 1})\n{doc.page_content}")
    return "\n\n".join(blocks)
