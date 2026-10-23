from pathlib import Path

import pytest

from app.ingestion.loader import load_pdf, load_pdfs

SAMPLE_PDF = Path("data/samples/ornek_ik_el_kitabi.pdf")


def test_load_pdf_returns_one_document_per_page():
    docs = load_pdf(SAMPLE_PDF)
    assert len(docs) == 3
    assert [d.metadata["page"] for d in docs] == [0, 1, 2]
    assert all(d.metadata["source"].endswith("ornek_ik_el_kitabi.pdf") for d in docs)


def test_load_pdf_preserves_turkish_text():
    text = "\n".join(d.page_content for d in load_pdf(SAMPLE_PDF))
    assert "Örnek Teknoloji" in text
    assert "Uzaktan Çalışma Politikası" in text
    assert "14 iş günü" in text


def test_load_pdf_missing_file():
    with pytest.raises(FileNotFoundError):
        load_pdf("yok.pdf")


def test_load_pdfs_reads_directory():
    assert len(load_pdfs(SAMPLE_PDF.parent)) == 3
