from __future__ import annotations

from src.normalization import normalize_prompt_json


def test_prompt_output_schema_is_valid_json() -> None:
    payload = {
        "metadata": {"company_name": "Sample PLC", "reporting_year": "2024"},
        "extracted_facts": {
            "company_overview": {"company_name": "Sample PLC", "reporting_year": "2024"},
        },
        "investor_friendly_insight": {"summary": "Sample summary"},
        "source_evidence": [],
        "missing_fields": [],
        "confidence_score": 0.8,
    }

    normalized = normalize_prompt_json(payload, "sample.pdf", "prompt_01", "gpt-5.2-chat")

    assert normalized["metadata"]["pdf_name"] == "sample.pdf"
    assert normalized["metadata"]["prompt_id"] == "prompt_01"
    assert "extracted_facts" in normalized
    assert "investor_friendly_insight" in normalized
