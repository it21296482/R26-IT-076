"""Extract annual report PDFs into page-level JSON.

Each extracted page keeps text, page number, optional tables, detected headings,
and a source reference so later outputs can cite where facts came from.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import ANNUAL_REPORTS_DIR, EXTRACTED_TEXT_DIR, ensure_directories
from .utils import slugify, write_json


SECTION_HEADING_PATTERN = re.compile(r"^(?:[A-Z][A-Z\s,&/-]{3,}|[0-9]+(?:\.[0-9]+)*\s+[A-Z][A-Za-z\s&/-]+)$")


def _require_pdf_dependencies():
    """Import PDF libraries only when extraction is actually requested."""
    try:
        import pymupdf as fitz
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "Missing PDF extraction dependencies. Run `python3 -m pip install PyMuPDF pdfplumber` "
            "or install everything with `python3 -m pip install -r requirements.txt` from component_2."
        ) from exc
    return fitz, pdfplumber


def detect_section_headings(page_text: str) -> list[str]:
    """Return simple heading candidates from a page of extracted text."""
    headings: list[str] = []
    for line in page_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) > 120:
            continue
        if SECTION_HEADING_PATTERN.match(stripped):
            headings.append(stripped)
    return headings[:12]


def extract_tables_from_page(pdf_path: Path, page_number: int) -> list[list[list[str]]]:
    """Try to extract tabular data from one PDF page."""
    _, pdfplumber = _require_pdf_dependencies()
    tables: list[list[list[str]]] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if page_number - 1 < len(pdf.pages):
                page = pdf.pages[page_number - 1]
                for table in page.extract_tables() or []:
                    cleaned_table = [[cell or "" for cell in row] for row in table if row]
                    if cleaned_table:
                        tables.append(cleaned_table)
    except Exception:
        return []
    return tables


def extract_pdf_pages(pdf_path: Path) -> dict[str, Any]:
    """Return the complete page-level extraction payload for one PDF."""
    fitz, _ = _require_pdf_dependencies()
    document = fitz.open(str(pdf_path))
    scanned_warning = False
    pages: list[dict[str, Any]] = []

    try:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if not text:
                scanned_warning = True
            page_payload = {
                "pdf_name": pdf_path.name,
                "page_number": index,
                "text": text,
                "detected_tables": extract_tables_from_page(pdf_path, index),
                "section_headings": detect_section_headings(text),
                "source_ref": f"{pdf_path.stem} page {index}",
            }
            pages.append(page_payload)
    finally:
        document.close()

    return {
        "pdf_name": pdf_path.name,
        "pdf_stem": pdf_path.stem,
        "page_count": len(pages),
        "warning": "Scanned PDF detected; OCR may be required." if scanned_warning else None,
        "pages": pages,
    }


def save_extracted_pdf(pdf_path: Path) -> Path:
    """Save one extracted PDF payload as data/extracted_text/{name}_pages.json."""
    ensure_directories()
    payload = extract_pdf_pages(pdf_path)
    output_path = EXTRACTED_TEXT_DIR / f"{slugify(pdf_path.stem)}_pages.json"
    write_json(output_path, payload)
    return output_path


def extract_all_pdfs() -> list[Path]:
    """Extract all PDFs found in data/annual_reports."""
    outputs: list[Path] = []
    for pdf_path in sorted(ANNUAL_REPORTS_DIR.glob("*.pdf")):
        outputs.append(save_extracted_pdf(pdf_path))
    return outputs
