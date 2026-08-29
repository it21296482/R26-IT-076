from src.fuse_insights import build_local_fusion, validate_output


def test_fusion_output_requires_all_sections():
    insight, warnings = validate_output({"headline": "A supported headline"})

    assert insight is not None
    assert warnings
    assert insight["non_advisory_note"] == (
        "This is an informational research summary, not buying or selling advice."
    )


def test_fusion_lists_are_normalized_and_limited():
    payload = {
        "headline": "Headline",
        "plain_language_overview": "Overview",
        "market_outlook": "Outlook",
        "company_report_takeaway": "Report",
        "external_context": "Context",
        "uncertainty": "Uncertainty",
        "non_advisory_note": "Ignored",
        "potential": [1, 2, 3, 4, 5, 6],
        "key_risks": [],
        "what_could_change_the_picture": [],
        "evidence_used": [],
    }

    insight, warnings = validate_output(payload)

    assert warnings == []
    assert insight["potential"] == ["1", "2", "3", "4", "5"]


def test_local_fusion_combines_deviation_report_and_context_in_plain_language():
    evidence = {
        "selected_stock": {"symbol": "BIL.N0000", "company_name": "Browns Investments PLC"},
        "market_evidence": {
            "current_price_lkr": 5.0,
            "horizons": [
                {"label": "4 trading days", "estimated_close_lkr": 4.98, "change_from_latest_pct": -0.4},
                {"label": "6 months", "status": "not_validated"},
            ],
            "anomaly": {
                "actual_price_lkr": 5.0,
                "expected_price_lkr": 5.03,
                "signed_deviation_lkr": -0.03,
                "liquidity_aware_score": 0.01,
                "threshold": 0.31,
                "detected": False,
            },
            "model_quality": {"advanced_model_beats_naive_mae": False},
        },
        "report_evidence": {
            "status": "completed",
            "insight": {
                "metadata": {"reporting_period": "31st March 2023"},
                "investor_friendly_insight": {
                    "summary": "Revenue grew, but the group recorded a loss.",
                    "key_strengths": ["Revenue increased."],
                    "key_concerns": ["The group recorded a loss."],
                },
            },
        },
        "external_context": {
            "articles": [
                {
                    "title": "Oil markets react to Middle East tensions",
                    "event_tags": ["geopolitical", "commodities"],
                    "sentiment": {"label": "negative"},
                }
            ],
            "external_factors": {"factors": []},
        },
    }

    insight = build_local_fusion(evidence)

    assert "latest price was LKR 5.00" in insight["plain_language_overview"]
    assert "warning level of 0.31" in insight["plain_language_overview"]
    assert "Revenue grew" in insight["plain_language_overview"]
    assert "Middle East tensions" in insight["plain_language_overview"]
    assert "does not prove" in insight["plain_language_overview"]
