from __future__ import annotations

from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")
pytest.importorskip("pdfplumber")

from src.pdf_extractor import extract_pdf_pages


def test_pdf_text_extraction_works(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample_report.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Sample PLC\nRevenue Rs. 120 million\nYear ended 31 March 2024")
    document.save(pdf_path)
    document.close()

    payload = extract_pdf_pages(pdf_path)

    assert payload["pdf_name"] == "sample_report.pdf"
    assert payload["page_count"] == 1
    assert "Revenue" in payload["pages"][0]["text"]
    assert payload["pages"][0]["source_ref"] == "sample_report page 1"
