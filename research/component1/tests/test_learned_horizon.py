import numpy as np
import pandas as pd
import pytest
from learned_horizon import CANDIDATES, feature_frame, fit_direct_horizon, learned_horizon_forecast


def data(kind="trend", n=1200):
    rng = np.random.default_rng(12)
    close = 20 * np.exp(np.arange(n) * .0005) if kind == "trend" else np.full(n, 20.)
    if kind == "random":
        close = 20 * np.exp(np.cumsum(rng.normal(0,.01,n)))
    return pd.DataFrame({"date":pd.bdate_range("2020-01-01",periods=n), "close":close,
                         "high":close*1.01,"low":close*.99,"volume":np.full(n,100000.)})


@pytest.mark.parametrize("kind", ["flat", "trend", "random"])
def test_new_horizon_models_have_finite_nested_bands_and_purged_evaluation(kind):
    forecast=learned_horizon_forecast(data(kind),120)
    assert len(forecast)==120
    assert np.isfinite(forecast.select_dtypes("number")).all().all()
    assert (forecast.lower_95>0).all()
    assert (forecast.lower_95<=forecast.lower_80).all()
    assert (forecast.lower_80<=forecast.predicted_close).all()
    assert (forecast.predicted_close<=forecast.upper_80).all()
    assert (forecast.upper_80<=forecast.upper_95).all()
    if kind=="trend":
        assert forecast.predicted_close.iloc[-1]>forecast.predicted_close.iloc[3]
    if kind=="flat":
        np.testing.assert_allclose(forecast.predicted_close,20.)
    for fit in forecast.attrs["calibration"]["horizons"].values():
        check=fit["holdout"]
        assert check["training_latest_target"]<check["calibration_first_origin"]
        assert check["calibration_latest_target"]<check["test_start_date"]
        assert fit["live_candidate"] in CANDIDATES
        assert fit["live_candidate"] == min(fit["live_selection_errors"], key=fit["live_selection_errors"].get)
        assert fit["selection_training_latest_target"] < fit["selection_tuning_first_origin"]
        assert fit["selection_tuning_latest_target"] < fit["live_calibration_first_origin"]


def test_test_prices_do_not_select_regression_parameters():
    raw=data("random")
    before=fit_direct_horizon(raw,feature_frame(raw),60)
    changed=raw.copy()
    changed.loc[1000:,"close"]*=1.2
    after=fit_direct_horizon(changed,feature_frame(changed),60)
    assert before["alpha"]==after["alpha"]
    assert before["tuning_errors"]==after["tuning_errors"]
    assert before["live_selection_errors"]==after["live_selection_errors"]
    assert before["live_candidate"]==after["live_candidate"]


def test_flat_prices_honestly_select_the_unchanged_price_baseline():
    raw = data("flat")
    fit = fit_direct_horizon(raw, feature_frame(raw), 120)
    assert set(fit["live_selection_errors"]) == set(CANDIDATES)
    assert fit["live_candidate"] == "persistence"
    assert fit["estimate"] == 20.


def test_new_observations_change_the_trained_forecast_without_cached_outputs():
    raw=data("random")
    before=learned_horizon_forecast(raw,120)
    changed=raw.copy()
    changed.loc[1190:,"close"]*=1.1
    after=learned_horizon_forecast(changed,120)
    assert not np.allclose(before.predicted_close,after.predicted_close)


def test_progress_reports_actual_completed_horizon_fits(capsys, monkeypatch):
    monkeypatch.setenv("CSE_MARKET_PROGRESS","1")
    learned_horizon_forecast(data(),120)
    output=capsys.readouterr().out
    assert output.count("CSE_PROGRESS ")==4
    assert '"horizon": 120' in output
