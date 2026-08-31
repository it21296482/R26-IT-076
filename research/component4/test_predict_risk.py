from predict_risk import predict


def _payload(stock: str) -> dict:
    return {
        "stock": stock,
        "close": 19.9,
        "volume": 1_680_918,
        "ma10": 20.1,
        "ma50": 20.5,
        "volatility": 0.45,
        "gold": 3400,
        "oil": 70,
        "vix": 21,
        "stock_date": "2026-08-31",
    }


def test_multiclass_explanation_returns_one_value_per_ranked_feature():
    result = predict(_payload("JKH"))

    assert result["status"] == "completed"
    assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert len(result["top_drivers"]) == 3
    assert len(result["global_drivers"]) == 3
    assert len({item["factor"] for item in result["top_drivers"]}) == 3


def test_unsupported_stock_is_not_encoded_as_another_company():
    result = predict(_payload("BIL"))

    assert result["status"] == "unavailable"
    assert result["code"] == "RISK_STOCK_NOT_SUPPORTED"
