from src.analyze_uploaded_report import company_identity_matches, normalize_text, validate_evidence


def test_company_identity_requires_distinctive_name_tokens():
    payload = {
        "pages": [
            {
                "page_number": 1,
                "text": "Browns Investments PLC Annual Report 2025/26",
            }
        ]
    }

    assert company_identity_matches(payload, "Browns Investments PLC", "BIL.N0000")
    assert not company_identity_matches(payload, "John Keells Holdings PLC", "JKH.N0000")


def test_evidence_validation_accepts_only_real_page_quotes():
    payload = {
        "pages": [
            {
                "page_number": 7,
                "text": "Revenue for the year was Rs. 12,500 million.",
            }
        ]
    }
    evidence = [
        {
            "field": "revenue_turnover",
            "value": "Rs. 12,500 million",
            "page_number": 7,
            "source_quote": "Revenue for the year was Rs. 12,500 million.",
        },
        {
            "field": "profit_after_tax",
            "value": "Rs. 2,000 million",
            "page_number": 7,
            "source_quote": "Profit after tax was Rs. 2,000 million.",
        },
    ]

    valid, warnings = validate_evidence(evidence, payload)

    assert len(valid) == 1
    assert valid[0]["field"] == "revenue_turnover"
    assert len(warnings) == 1


def test_quote_matching_normalizes_line_breaks_and_spacing():
    assert normalize_text("Revenue\n for   the year") == "revenue for the year"
