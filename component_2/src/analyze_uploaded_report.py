"""Analyze one uploaded financial report for the unified application.

The research benchmark remains an offline experiment. Production requests reuse the
selected prompt, run it once against the uploaded PDF, and validate every returned
source quote before the result can be marked complete.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.llm_client import LLMClient
    from src.local_report_analysis import build_local_report_insight
    from src.pdf_extractor import extract_pdf_pages
    from src.prompts import prompt_definitions
    from src.retrieval import build_retrieval_context
else:
    from .llm_client import LLMClient
    from .local_report_analysis import build_local_report_insight
    from .pdf_extractor import extract_pdf_pages
    from .prompts import prompt_definitions
    from .retrieval import build_retrieval_context


SELECTED_PROMPT_ID = "prompt_08"
MIN_EXTRACTED_CHARACTERS = 500
MAX_CONTEXT_CHARACTERS = 60_000
GENERIC_COMPANY_WORDS = {
    "company",
    "holdings",
    "limited",
    "ltd",
    "plc",
    "group",
    "the",
}


def normalize_text(value: Any) -> str:
    """Normalize extracted text for conservative identity and quote matching."""
    text = str(value or "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    return re.sub(r"\s+", " ", text).strip().lower()


def company_identity_matches(extracted_payload: dict[str, Any], company_name: str, symbol: str) -> bool:
    """Require the selected company name or its distinctive tokens in the PDF text."""
    report_text = normalize_text(" ".join(page.get("text", "") for page in extracted_payload.get("pages", [])[:30]))
    company_phrase = normalize_text(company_name)
    if company_phrase and company_phrase in report_text:
        return True

    distinctive_tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", company_phrase)
        if len(token) >= 4 and token not in GENERIC_COMPANY_WORDS
    ]
    if distinctive_tokens and all(token in report_text for token in distinctive_tokens):
        return True

    ticker = normalize_text(symbol).split(".")[0]
    return len(ticker) >= 4 and re.search(rf"\b{re.escape(ticker)}\b", report_text) is not None


def validate_evidence(
    evidence: Any,
    extracted_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Keep only evidence containing an exact normalized quote on one real page."""
    pages = {
        int(page["page_number"]): normalize_text(page.get("text", ""))
        for page in extracted_payload.get("pages", [])
    }
    valid: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not isinstance(evidence, list):
        return [], ["The model did not return source evidence as a list."]

    for index, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            warnings.append(f"Evidence item {index} was not a structured object.")
            continue
        try:
            page_number = int(item.get("page_number"))
        except (TypeError, ValueError):
            warnings.append(f"Evidence item {index} did not contain one valid page number.")
            continue

        quote = normalize_text(item.get("source_quote"))
        field = str(item.get("field") or "").strip()
        if not field or len(quote) < 12:
            warnings.append(f"Evidence item {index} was missing a field name or usable quote.")
            continue
        if page_number not in pages or quote not in pages[page_number]:
            warnings.append(f"Evidence item {index} could not be verified on page {page_number}.")
            continue

        valid.append(
            {
                "field": field,
                "value": item.get("value"),
                "page_number": page_number,
                "source_quote": str(item.get("source_quote")).strip(),
            }
        )

    return valid, warnings


def selected_prompt_text() -> str:
    """Load the best prompt selected by the documented prompt experiment."""
    for definition in prompt_definitions():
        if definition["prompt_id"] == SELECTED_PROMPT_ID:
            return definition["prompt_text"]
    raise RuntimeError(f"Selected prompt {SELECTED_PROMPT_ID} is unavailable.")


def build_runtime_prompt(
    extracted_payload: dict[str, Any],
    company_name: str,
    symbol: str,
) -> str:
    """Add evidence constraints missing from the original benchmark prompt."""
    context = build_retrieval_context(extracted_payload, max_pages_per_field=2)[:MAX_CONTEXT_CHARACTERS]
    return f"""
{selected_prompt_text()}

Runtime verification requirements:
- The selected company is {company_name} ({symbol}).
- Set metadata.pdf_name to {extracted_payload['pdf_name']}.
- Set metadata.prompt_id to {SELECTED_PROMPT_ID}.
- Use only the report context below. Do not use outside facts.
- Every source_evidence item must be an object containing: field, value,
  page_number as one integer, and source_quote copied exactly from that page.
- Include evidence for every important numeric claim used in the summary.
- If a value cannot be supported by an exact quote, return null and add its
  field name to missing_fields.
- Do not estimate missing values and do not provide buy, sell, or hold advice.

Report context:
{context}
""".strip()


def external_explanation_enabled() -> bool:
    """Require an explicit opt-in so a stale local credential cannot break requests."""
    return os.getenv("USE_AZURE_OPENAI", "false").strip().lower() in {"1", "true", "yes"}


def locally_grounded_result(
    extracted: dict[str, Any],
    pdf_path: Path,
    company_name: str,
    symbol: str,
    extracted_characters: int,
) -> dict[str, Any]:
    """Produce and verify the deterministic fallback against the source pages."""
    insight = build_local_report_insight(extracted, company_name, symbol, SELECTED_PROMPT_ID)
    raw_evidence = insight.get("source_evidence", [])
    valid_evidence, evidence_warnings = validate_evidence(raw_evidence, extracted)
    insight["source_evidence"] = valid_evidence
    important_fields = {"revenue", "profit_after_tax", "total_assets", "total_equity"}
    verified_fields = {item["field"] for item in valid_evidence}
    narrative_count = sum(field.startswith("operational_") for field in verified_fields)
    enough_evidence = len(valid_evidence) >= 3 and (
        bool(important_fields & verified_fields) or narrative_count >= 5
    )
    warnings = evidence_warnings
    if not enough_evidence:
        warnings.append("The report text was readable, but too few standard statement rows could be verified.")
    return {
        "status": "completed" if enough_evidence else "needs_review",
        "report": {
            "filename": pdf_path.name,
            "page_count": extracted.get("page_count", 0),
            "company_match": True,
            "extracted_characters": extracted_characters,
        },
        "insight": insight,
        "evidence_validation": {
            "valid_count": len(valid_evidence),
            "rejected_count": max(0, len(raw_evidence) - len(valid_evidence)),
            "selected_prompt_id": SELECTED_PROMPT_ID,
            "method": "verified_statement_rows_and_operational_highlights",
        },
        "warnings": warnings,
    }


def analyze_report(pdf_path: Path, company_name: str, symbol: str) -> dict[str, Any]:
    """Extract, analyze, validate, and return one report result."""
    extracted = extract_pdf_pages(pdf_path)
    extracted_characters = sum(len(page.get("text", "")) for page in extracted.get("pages", []))
    warnings: list[str] = []

    if extracted_characters < MIN_EXTRACTED_CHARACTERS:
        return {
            "status": "needs_review",
            "report": {
                "filename": pdf_path.name,
                "page_count": extracted.get("page_count", 0),
                "company_match": False,
                "extracted_characters": extracted_characters,
            },
            "insight": None,
            "evidence_validation": {"valid_count": 0, "rejected_count": 0},
            "warnings": ["The PDF did not contain enough machine-readable text. OCR is required."],
        }

    company_match = company_identity_matches(extracted, company_name, symbol)
    if not company_match:
        return {
            "status": "rejected",
            "report": {
                "filename": pdf_path.name,
                "page_count": extracted.get("page_count", 0),
                "company_match": False,
                "extracted_characters": extracted_characters,
            },
            "insight": None,
            "evidence_validation": {"valid_count": 0, "rejected_count": 0},
            "warnings": ["The uploaded report could not be matched to the selected company."],
        }

    if not external_explanation_enabled():
        return locally_grounded_result(
            extracted, pdf_path, company_name, symbol, extracted_characters
        )

    response = LLMClient().run_json_prompt(build_runtime_prompt(extracted, company_name, symbol))
    if response.get("error") or not isinstance(response.get("parsed_output"), dict):
        return locally_grounded_result(
            extracted, pdf_path, company_name, symbol, extracted_characters
        )

    insight = response["parsed_output"]
    raw_evidence = insight.get("source_evidence", [])
    valid_evidence, evidence_warnings = validate_evidence(raw_evidence, extracted)
    warnings.extend(evidence_warnings)
    insight["source_evidence"] = valid_evidence
    insight.setdefault("metadata", {})["pdf_name"] = pdf_path.name
    insight["metadata"]["prompt_id"] = SELECTED_PROMPT_ID
    insight["metadata"]["selected_symbol"] = symbol
    insight["investor_friendly_insight"] = insight.get("investor_friendly_insight") or {}
    insight["investor_friendly_insight"]["non_advisory_note"] = (
        "This is an informational summary for decision support, not buying or selling advice."
    )

    rejected_count = max(0, len(raw_evidence) - len(valid_evidence)) if isinstance(raw_evidence, list) else 0
    status = "completed" if valid_evidence and not warnings else "needs_review"
    if not valid_evidence:
        warnings.append("No report quote passed source verification; the result must not be treated as grounded.")

    return {
        "status": status,
        "report": {
            "filename": pdf_path.name,
            "page_count": extracted.get("page_count", 0),
            "company_match": True,
            "extracted_characters": extracted_characters,
        },
        "insight": insight,
        "evidence_validation": {
            "valid_count": len(valid_evidence),
            "rejected_count": rejected_count,
            "selected_prompt_id": SELECTED_PROMPT_ID,
            "runtime_seconds": response.get("runtime_seconds"),
        },
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze one uploaded CSE company report.")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--symbol", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = analyze_report(args.pdf.resolve(), args.company_name, args.symbol.upper())
    except Exception as error:  # noqa: BLE001
        result = {
            "status": "failed",
            "report": {"filename": args.pdf.name},
            "insight": None,
            "evidence_validation": {"valid_count": 0, "rejected_count": 0},
            "warnings": [str(error)],
        }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
