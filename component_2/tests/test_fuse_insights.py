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
        "risk_outlook": "Risk",
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
        "risk_evidence": {
            "status": "completed",
            "risk_level": "HIGH",
            "plain_explanation": "The combined market-risk reading is HIGH.",
            "top_drivers": [{"label": "Recent price variability", "meaning": "Recent prices were less stable."}],
        },
    }

    insight = build_local_fusion(evidence)

    assert "latest price was LKR 5.00" in insight["plain_language_overview"]
    assert "warning level of 0.31" in insight["plain_language_overview"]
    assert "Revenue grew" in insight["plain_language_overview"]
    assert "Middle East tensions" in insight["plain_language_overview"]
    assert "does not prove" in insight["plain_language_overview"]
    assert "combined market-risk reading is HIGH" in insight["plain_language_overview"]
    assert insight["decision_balance"]["label"] == "Risk-heavy despite upside possibilities"


def test_local_fusion_marks_downside_heavy_price_range_as_risk_heavy():
    evidence = {
        "selected_stock": {"symbol": "BIL.N0000", "company_name": "Browns Investments PLC"},
        "market_evidence": {
            "current_price_lkr": 5.0,
            "horizons": [
                {
                    "label": "3 months",
                    "key": "3m",
                    "estimated_close_lkr": 4.65,
                    "change_from_latest_pct": -7.0,
                    "lower_80_lkr": 2.9,
                    "upper_80_lkr": 6.4,
                    "lower_95_lkr": 1.4,
                    "upper_95_lkr": 7.9,
                }
            ],
            "anomaly": {"detected": False},
            "model_quality": {},
        },
        "report_evidence": {
            "status": "completed",
            "insight": {
                "investor_friendly_insight": {
                    "summary": "Revenue grew, but the company recorded a loss.",
                    "key_strengths": ["Revenue increased."],
                    "key_concerns": ["The company recorded a loss."],
                }
            },
        },
        "external_context": {"articles": [], "external_factors": {"factors": []}},
    }

    insight = build_local_fusion(evidence)

    assert insight["decision_balance"]["label"] == "Risk-heavy despite upside possibilities"
    assert "measured downside is larger" in insight["decision_balance"]["plain_conclusion"]


def test_summary_explains_aspi_comparison_and_conditional_upside():
    evidence = {
        "selected_stock": {"symbol": "BIL.N0000", "company_name": "Browns Investments PLC"},
        "market_evidence": {
            "current_price_lkr": 5.0,
            "horizons": [{
                "label": "3 months",
                "key": "3m",
                "estimated_close_lkr": 4.65,
                "change_from_latest_pct": -7.0,
                "lower_80_lkr": 2.9,
                "upper_80_lkr": 6.4,
                "lower_95_lkr": 1.4,
                "upper_95_lkr": 7.9,
            }],
            "anomaly": {"detected": False},
            "model_quality": {},
        },
        "report_evidence": {
            "status": "completed",
            "insight": {"investor_friendly_insight": {
                "summary": "Revenue and operating profit improved.",
                "key_strengths": ["Revenue increased."],
                "key_concerns": ["Finance costs remain high."],
            }},
        },
        "external_context": {
            "articles": [{"title": "BIL reports growth", "sentiment": {"label": "positive"}}],
            "external_factors": {"factors": [], "marketComparison": {
                "stockChangePct": -2.0,
                "aspiChangePct": 0.5,
                "classification": "stock_specific_weakness",
                "interpretation": "The stock declined while the ASPI increased, so the weakness was specific to this stock.",
            }},
        },
    }

    insight = build_local_fusion(evidence)

    assert "stock changed -2.0% while the ASPI changed +0.5%" in insight["plain_language_overview"]
    assert "specific to this stock" in insight["plain_language_overview"]
    assert "favourable 3 months range of LKR 6.40 (+28.0% from today)" in insight["plain_language_overview"]
    assert "not a prediction" in insight["conditional_upside"]


def test_normal_daily_movement_does_not_erase_prolonged_shock_risk_or_invent_a_peace_price():
    evidence = {
        "selected_stock": {"symbol": "JKH.N0000", "company_name": "John Keells Holdings PLC"},
        "market_evidence": {"current_price_lkr": 18., "anomaly": {"detected": False}, "horizons": [{
            "key": "3m", "label": "3 months", "estimated_close_lkr": 18.2,
            "upper_80_lkr": 20., "lower_80_lkr": 16., "upper_95_lkr": 22., "lower_95_lkr": 14.,
        }]},
        "report_evidence": {"status": "completed", "insight": {"investor_friendly_insight": {
            "summary": "Hotel and transportation profits improved, but finance costs remain high.",
            "key_strengths": ["Hotel performance improved."], "key_concerns": ["Debt remains high."],
        }}},
        "news_sentiment_evidence": {"articles": [{"title": "Disaster recovery update", "event_tags": ["disaster_recovery"]}]},
    }
    insight = build_local_fusion(evidence)
    context = insight["shock_context"]
    assert "does not mean" in context["anomaly_context"]
    assert "Middle East" in context["recovery_outlook"]
    assert "Ditwah" in context["recovery_outlook"]
    assert "has not established a validated price" in context["range_note"]
    assert context["event_conditioned_price_available"] is False
    assert context["horizon_ranges"][0]["favourable_80_lkr"] == 20.
    assert "financing" in " ".join(context["company_exposure"])
    assert "No new unusual daily movement" in insight["plain_language_overview"]


def test_unverified_report_and_missing_anomaly_do_not_turn_into_recovery_evidence():
    insight = build_local_fusion({"report_evidence": {"status": "needs_review", "insight": {
        "investor_friendly_insight": {"summary": "Hotel profits doubled."},
    }}})
    assert "absence of a result does not mean normal" in insight["shock_context"]["anomaly_context"]
    assert "has not been established" in insight["shock_context"]["company_exposure"][0]
    assert "No dated conflict" in insight["shock_context"]["evidence_status"]
