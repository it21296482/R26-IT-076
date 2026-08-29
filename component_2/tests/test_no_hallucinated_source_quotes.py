from __future__ import annotations

from src.evaluate_prompts import validate_source_quote


def test_source_quotes_exist_inside_extracted_text() -> None:
    extracted_payload = {
        "pages": [
            {
                "page_number": 3,
                "text": "Revenue for the year amounted to Rs. 120 million according to the annual report.",
            }
        ]
    }

    assert validate_source_quote(
        extracted_payload,
        3,
        "Revenue for the year amounted to Rs. 120 million",
    )
    assert not validate_source_quote(
        extracted_payload,
        3,
        "This quote does not exist in the report",
    )
