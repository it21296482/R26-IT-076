import numpy as np
import pandas as pd
import pytest
from train_stock_on_demand import fit_stock
from train_cse_risk_model import prepare_dataset
from predict_risk import predict
from test_predict_risk import _payload


def fixtures(symbol="COMB.X0000", count=600):
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2022-01-01", periods=count)
    history = pd.DataFrame({"Date": dates, "Symbol": symbol,
        "Close": 30 * np.exp(np.cumsum(rng.normal(0, .025, count))), "Volume": rng.integers(1000, 2000000, count)})
    factors = pd.DataFrame({"Date": dates, "Gold": 2000 + np.cumsum(rng.normal(0, 20, count)),
        "Oil": 80 + np.cumsum(rng.normal(0, .5, count)), "VIX": rng.uniform(12, 36, count)})
    return history, factors


def test_fresh_fit_preserves_security_identity_and_heldout_metrics():
    history, factors = fixtures()
    bundle = fit_stock(history, "COMB.X0000", factors)
    metadata = bundle[2]
    assert metadata["fresh_fit"]
    assert metadata["supported_stocks"] == ["COMB.X0000"]
    detail = metadata["split_details"]["COMB.X0000"]
    assert detail["train_end"] < detail["test_start"]
    assert detail["test_rows"] >= 50
    assert len(metadata["history_sha256"]) == 64
    result = predict(_payload("COMB.X0000"), bundle)
    assert result["status"] == "completed"
    assert len(result["global_drivers"]) == 6
    assert predict(_payload("COMB.N0000"), bundle)["status"] == "unavailable"


def test_prior_global_close_prevents_same_day_us_close_leakage():
    history, factors = fixtures()
    prepared = prepare_dataset(history, factors, preserve_symbols=True, prior_global_close=True)
    row = prepared.iloc[20]
    original = factors[factors.Date < row.Date].iloc[-1]
    assert row.Gold == original.Gold
    assert row.Stock == "COMB.X0000"


def test_insufficient_history_or_wrong_security_fails_without_proxy():
    history, factors = fixtures(count=100)
    with pytest.raises(ValueError, match="Not enough"):
        fit_stock(history, "COMB.X0000", factors)
    with pytest.raises(ValueError, match="exactly the selected"):
        fit_stock(history, "COMB.N0000", factors)
