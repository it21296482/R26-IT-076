from __future__ import annotations

from collections import OrderedDict

from src.evaluate_prompts import coverage_score, numeric_accuracy_score


def test_scoring_formula_returns_between_zero_and_one() -> None:
    expected_fields = OrderedDict(
        {
            "revenue_turnover": {"expected_value": "Rs. 120 million"},
            "profit_after_tax": {"expected_value": "Rs. 30 million"},
        }
    )
    extracted_fields = OrderedDict({"revenue_turnover": "Rs. 120 million", "profit_after_tax": "Rs. 28.5 million"})

    coverage = coverage_score(expected_fields, extracted_fields)
    numeric = numeric_accuracy_score(expected_fields, extracted_fields)

    assert 0.0 <= coverage <= 1.0
    assert 0.0 <= numeric <= 1.0
