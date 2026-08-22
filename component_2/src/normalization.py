"""Normalize LLM responses into the standard output schema.

Different prompts may return slightly different JSON shapes. Normalization
makes them comparable before scoring and final report generation.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .schemas import INVESTOR_FIELD_GROUPS, build_standard_output_schema, now_iso
from .utils import flatten_text


def build_field_to_category() -> dict[str, str]:
    """Map each field name to its parent category."""
    mapping: dict[str, str] = {}
    for category, fields in INVESTOR_FIELD_GROUPS.items():
        for field in fields:
            mapping[field] = category
    return mapping


FIELD_TO_CATEGORY = build_field_to_category()


def normalize_source_evidence(raw_evidence: Any) -> list[dict[str, Any]]:
    """Coerce LLM evidence into the required list-of-objects schema."""
    if not isinstance(raw_evidence, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in raw_evidence:
        if isinstance(item, dict):
            normalized.append(
                {
                    "field": item.get("field", ""),
                    "value": item.get("value", ""),
                    "page_number": item.get("page_number", ""),
                    "source_quote": item.get("source_quote", ""),
                }
            )
        elif isinstance(item, str):
            normalized.append(
                {
                    "field": "",
                    "value": "",
                    "page_number": "",
                    "source_quote": item,
                }
            )
    return normalized


def normalize_prompt_json(raw_output: Any, pdf_name: str, prompt_id: str, model_name: str) -> OrderedDict[str, Any]:
    """Coerce one LLM response into the required standard schema."""
    template = build_standard_output_schema()
    result: OrderedDict[str, Any] = OrderedDict(template)

    if isinstance(raw_output, dict):
        metadata = raw_output.get("metadata", {})
        result["metadata"].update(metadata if isinstance(metadata, dict) else {})

        extracted = raw_output.get("extracted_facts", {})
        if isinstance(extracted, dict):
            for category, fields in result["extracted_facts"].items():
                candidate = extracted.get(category, {})
                if isinstance(candidate, dict):
                    for field in fields:
                        result["extracted_facts"][category][field] = candidate.get(field)

        insight = raw_output.get("investor_friendly_insight", {})
        if isinstance(insight, dict):
            result["investor_friendly_insight"].update(insight)

        result["source_evidence"] = normalize_source_evidence(raw_output.get("source_evidence", []))
        missing_fields = raw_output.get("missing_fields", [])
        result["missing_fields"] = missing_fields if isinstance(missing_fields, list) else []
        confidence = raw_output.get("confidence_score", 0.0)
        try:
            result["confidence_score"] = float(confidence)
        except Exception:
            result["confidence_score"] = 0.0

    result["metadata"]["pdf_name"] = pdf_name
    result["metadata"]["prompt_id"] = prompt_id
    result["metadata"]["model"] = model_name
    result["metadata"]["generated_at"] = now_iso()

    company_name = find_field(result, "company_name")
    reporting_year = find_field(result, "reporting_year")
    if company_name:
        result["metadata"]["company_name"] = company_name
    if reporting_year:
        result["metadata"]["reporting_year"] = reporting_year

    result["investor_friendly_insight"]["non_advisory_note"] = "This is an informational summary only and not financial advice."
    return result


def find_field(prompt_output: dict[str, Any], field_name: str) -> Any:
    """Find one field value inside normalized extracted_facts."""
    category = FIELD_TO_CATEGORY.get(field_name)
    if not category:
        return None
    return prompt_output.get("extracted_facts", {}).get(category, {}).get(field_name)


def flatten_prompt_fields(prompt_output: dict[str, Any]) -> OrderedDict[str, Any]:
    """Flatten nested facts so scoring can compare fields directly."""
    flattened: OrderedDict[str, Any] = OrderedDict()
    for category, fields in INVESTOR_FIELD_GROUPS.items():
        category_payload = prompt_output.get("extracted_facts", {}).get(category, {})
        for field_name in fields:
            flattened[field_name] = category_payload.get(field_name)
    return flattened


def collect_missing_fields(prompt_output: dict[str, Any]) -> list[str]:
    """Update missing_fields based on empty normalized values."""
    flattened = flatten_prompt_fields(prompt_output)
    missing = [field for field, value in flattened.items() if value in (None, "", [])]
    prompt_output["missing_fields"] = missing
    return missing
