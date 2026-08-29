"""Build expected source-grounded answers from extracted PDF pages.

This creates the reference answers used to evaluate the 10 prompts. Values are
derived from actual extracted report text and include page/source snippets.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from .config import EXPECTED_OUTPUTS_DIR, EXTRACTED_TEXT_DIR, ensure_directories
from .retrieval import FIELD_METADATA, discovery_summary, rank_pages_for_field
from .schemas import INVESTOR_FIELD_GROUPS
from .utils import has_meaningful_value, normalize_whitespace, read_json, safe_excerpt, slugify, write_json


VALUE_PATTERN = re.compile(
    r"(?:(?:rs\.?|lkr|usd)\s*)?\d[\d,\s]*(?:\.\d+)?\s*(?:thousand|million|billion|trillion|%)?",
    re.IGNORECASE,
)


def infer_value_from_page(field_name: str, page: dict[str, Any]) -> tuple[str | None, str | None]:
    """Find a likely field value by searching around matching keywords."""
    text = page.get("text", "")
    aliases = FIELD_METADATA[field_name]["aliases"]
    for alias in aliases:
        match = re.search(re.escape(alias), text, re.IGNORECASE)
        if not match:
            continue
        snippet = safe_excerpt(text, match.start(), match.end())
        if FIELD_METADATA[field_name].get("numeric"):
            nearby = VALUE_PATTERN.findall(text[match.end() : match.end() + 220])
            if nearby:
                return normalize_whitespace(nearby[0]), snippet
            before = VALUE_PATTERN.findall(text[max(0, match.start() - 220) : match.start()])
            if before:
                return normalize_whitespace(before[-1]), snippet
        return snippet, snippet
    return None, None


def infer_special_fields(field_name: str, ranked_pages: list[dict[str, Any]], pdf_name: str) -> tuple[str | None, str | None, int | None]:
    """Use custom rules for fields that are not simple numeric lookups."""
    if not ranked_pages:
        return None, None, None

    for page in ranked_pages:
        text = page.get("text", "")
        if field_name == "company_name":
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines[:20]:
                if any(token in line.lower() for token in ["plc", "limited", "holdings"]):
                    return line, line, page["page_number"]
        if field_name == "reporting_year":
            year_match = re.search(r"(?:year ended|for the year ended|annual report)\s+([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{4}/[0-9]{2}|[0-9]{4})", text, re.IGNORECASE)
            if year_match:
                snippet = safe_excerpt(text, year_match.start(), year_match.end())
                return year_match.group(1), snippet, page["page_number"]

    page = ranked_pages[0]
    value, snippet = infer_value_from_page(field_name, page)
    return value, snippet, page["page_number"] if value else None


def build_expected_output_for_pdf(extracted_payload: dict[str, Any]) -> dict[str, Any]:
    """Build the expected source-backed field set for one PDF payload."""
    expected_fields: OrderedDict[str, Any] = OrderedDict()

    for category, fields in INVESTOR_FIELD_GROUPS.items():
        for field_name in fields:
            ranked_pages = rank_pages_for_field(extracted_payload, field_name, top_k=3)
            value, source_text, page_number = infer_special_fields(field_name, ranked_pages, extracted_payload["pdf_name"])
            if not value and ranked_pages:
                value, source_text = infer_value_from_page(field_name, ranked_pages[0])
                page_number = ranked_pages[0]["page_number"] if value else None

            payload = {
                "category": category,
                "expected_value": value if has_meaningful_value(value) else None,
                "source_text": normalize_whitespace(source_text)[:360] if source_text else None,
                "page_number": page_number,
                "confidence": round(0.55 + min(0.4, 0.1 * len(ranked_pages)), 2) if value else 0.0,
            }
            if not value:
                payload["status"] = "not_found"
            expected_fields[field_name] = payload

    return {
        "pdf_name": extracted_payload["pdf_name"],
        "discovery_summary": discovery_summary(extracted_payload),
        "expected_outputs": expected_fields,
    }


def build_expected_output_from_path(extracted_json_path: Path) -> Path:
    """Read extracted text JSON and write one expected output JSON."""
    ensure_directories()
    extracted_payload = read_json(extracted_json_path)
    expected_payload = build_expected_output_for_pdf(extracted_payload)
    output_path = EXPECTED_OUTPUTS_DIR / f"{slugify(extracted_payload['pdf_stem'])}_expected.json"
    write_json(output_path, expected_payload)
    return output_path


def build_all_expected_outputs() -> list[Path]:
    """Create expected outputs for every extracted annual report."""
    outputs: list[Path] = []
    for extracted_json_path in sorted(EXTRACTED_TEXT_DIR.glob("*_pages.json")):
        outputs.append(build_expected_output_from_path(extracted_json_path))
    return outputs
