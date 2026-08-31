import json

import pandas as pd

from predict_risk import METADATA_PATH, predict
from train_cse_risk_model import current_risk_score


def _payload(stock: str) -> dict:
    return {
        "stock": stock,
        "close": 19.9,
        "volume": 1_680_918,
        "ma10": 20.1,
        "ma50": 20.5,
        "volatility": 0.45,
        "return20_pct": -4.2,
        "drawdown20_pct": -6.5,
        "volatility_pct": 2.2,
        "volume_ratio20": 1.4,
        "gold": 3400,
        "oil": 70,
        "vix": 21,
        "gold_change30d_pct": 3.2,
        "oil_change30d_pct": -4.1,
        "vix_change30d_pct": 8.0,
        "stock_date": "2026-08-31",
    }


def test_multiclass_explanation_returns_one_value_per_ranked_feature():
    for stock in ("BIL", "JKH"):
        result = predict(_payload(stock))

        assert result["status"] == "completed"
        assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
        assert len(result["top_drivers"]) == 3
        assert len(result["global_drivers"]) == 6
        assert len({item["factor"] for item in result["top_drivers"]}) == 3
        assert result["model_validation"]["chronological_test_macro_f1"] > 0.8


def test_unsupported_stock_is_not_encoded_as_another_company():
    result = predict(_payload("HHL"))

    assert result["status"] == "unavailable"
    assert result["code"] == "RISK_STOCK_NOT_SUPPORTED"


def test_stressed_observable_conditions_produce_a_higher_risk_index():
    frame = pd.DataFrame([
        {
            "VolatilityPct": 1.0,
            "Return20Pct": 4.0,
            "Drawdown20Pct": 0.0,
            "VIX": 14.0,
            "OilChange30dPct": 1.0,
            "GoldChange30dPct": 1.0,
            "VolumeRatio20": 1.0,
        },
        {
            "VolatilityPct": 10.0,
            "Return20Pct": -25.0,
            "Drawdown20Pct": -18.0,
            "VIX": 36.0,
            "OilChange30dPct": 25.0,
            "GoldChange30dPct": 18.0,
            "VolumeRatio20": 5.0,
        },
    ])
    scores = current_risk_score(frame)
    assert scores.iloc[1] > scores.iloc[0]


def test_stored_chronological_evaluation_beats_the_baseline_and_supports_both_stocks():
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["supported_stocks"] == ["BIL", "JKH"]
    assert metadata["test_metrics"]["macro_f1"] > metadata["majority_baseline_macro_f1"]
    assert metadata["global_indicator_macro_f1_change"] > 0
