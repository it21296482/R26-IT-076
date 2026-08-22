from __future__ import annotations

from src.expected_output_builder import build_expected_output_for_pdf


def test_expected_output_schema_is_valid() -> None:
    extracted_payload = {
        "pdf_name": "sample.pdf",
        "pdf_stem": "sample",
        "pages": [
            {
                "pdf_name": "sample.pdf",
                "page_number": 1,
                "text": "Sample PLC Annual Report 2024 Revenue Rs. 120 million total assets Rs. 500 million",
                "detected_tables": [],
                "section_headings": ["ANNUAL REPORT"],
                "source_ref": "sample page 1",
            }
        ],
    }
    expected_payload = build_expected_output_for_pdf(extracted_payload)

    assert expected_payload["pdf_name"] == "sample.pdf"
    assert "expected_outputs" in expected_payload
    assert "company_name" in expected_payload["expected_outputs"]
    assert "expected_value" in expected_payload["expected_outputs"]["company_name"]
