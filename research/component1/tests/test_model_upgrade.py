from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from component1_research import (
    add_anomaly_columns, apply_causal_anomaly_thresholds, engineer_features,
    relative_sequence_features, DEFAULT_FEATURE_COLUMNS,
)
from horizon_forecast import candidate_paths, calibrated_horizon_forecast, choose_candidate


def history(n=1000, kind="flat"):
    rng = np.random.default_rng(24)
    if kind == "flat":
        close = np.full(n, 20.0)
    elif kind == "trend":
        close = 20 * np.exp(np.arange(n) * 0.001)
    else:
        close = 20 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    return pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=n),
                         "open": close, "high": close * 1.01, "low": close * .99,
                         "close": close, "volume": rng.integers(1000, 2_000_000, n)})


def test_future_shock_cannot_rewrite_past_proxy_labels():
    raw = history(kind="random")
    before = engineer_features(raw.iloc[:700]).proxy_anomaly_label
    changed = raw.copy()
    changed.loc[700:, "close"] *= 10
    after = engineer_features(changed).proxy_anomaly_label.iloc[:700]
    pd.testing.assert_series_equal(before, after)


@pytest.mark.parametrize("kind", ["flat", "trend", "random"])
def test_horizon_paths_are_finite_positive_and_nested(kind):
    forecast = calibrated_horizon_forecast(history(kind=kind), 120)
    assert len(forecast) == 120
    assert np.isfinite(forecast.select_dtypes("number")).all().all()
    assert (forecast.lower_95 > 0).all()
    assert (forecast.lower_95 <= forecast.lower_80).all()
    assert (forecast.lower_80 <= forecast.predicted_close).all()
    assert (forecast.upper_80 <= forecast.upper_95).all()
    if kind == "flat":
        assert np.allclose(forecast.predicted_close, 20)
    for fit in forecast.attrs["calibration"]["horizons"].values():
        check = fit["holdout"]
        if check["status"] == "retrospective_purged_holdout":
            assert check["calibration_end_date"] < check["test_start_date"]


def test_persistence_wins_over_bad_candidates():
    rows = pd.DataFrame({"actual": np.ones(30), "anchor": np.ones(30), "persistence": np.ones(30),
                         **{name: np.full(30, 2.0) for name in candidate_paths(np.ones(100), 4) if name != "persistence"}})
    assert choose_candidate(rows)[0] == "persistence"


def test_relative_features_do_not_depend_on_price_unit():
    raw = engineer_features(history(kind="random")).dropna(subset=DEFAULT_FEATURE_COLUMNS)
    array = raw[DEFAULT_FEATURE_COLUMNS].tail(60).to_numpy(np.float32).reshape(3, 20, -1)
    changed = array.copy()
    for name in ("open", "high", "low", "close", "sma_5", "sma_10", "sma_20", "sma_50", "ema_12", "ema_26", "moving_average_gap", "atr_14"):
        changed[:, :, DEFAULT_FEATURE_COLUMNS.index(name)] *= 10
    np.testing.assert_allclose(relative_sequence_features(array), relative_sequence_features(changed), rtol=1e-4, atol=1e-6)


def scored(n=500):
    raw = engineer_features(history(n, "random")).iloc[60:].copy()
    raw["actual_price"] = raw.close
    raw["predicted_price"] = raw.prev_close
    return add_anomaly_columns(raw, 1_000_000, 1e-6, downside_band=.3, upside_band=.3,
                               liquidity_threshold=1.0, prediction_band_threshold=1.1)


def test_anomaly_cutoff_excludes_current_and_future_scores():
    raw = scored()
    before = apply_causal_anomaly_thresholds(raw.iloc[:200], raw.iloc[200:], 1.0, 1.1)
    changed = raw.copy()
    changed.iloc[300:, changed.columns.get_loc("liquidity_aware_anomaly_score")] = 1e10
    after = apply_causal_anomaly_thresholds(changed.iloc[:200], changed.iloc[200:], 1.0, 1.1)
    np.testing.assert_array_equal(before.applied_liquidity_threshold.iloc[:101], after.applied_liquidity_threshold.iloc[:101])


def test_zero_volume_is_not_liquidity_confirmation():
    raw = scored().iloc[:1].copy()
    raw["volume"] = 0
    result = add_anomaly_columns(raw, 1_000_000, 1e-6, liquidity_threshold=.1)
    assert not result.liquidity_anomaly_flag.iloc[0]
    assert not result.score_reliable.iloc[0]
    assert result.liquidity_aware_anomaly_score.iloc[0] > .1


def test_bad_history_is_rejected():
    raw = history()
    raw.loc[10, "close"] = -1
    with pytest.raises(ValueError, match="positive"):
        calibrated_horizon_forecast(raw, 120)
    raw = history()
    raw.loc[10, "date"] = raw.date.iloc[9]
    with pytest.raises(ValueError, match="Duplicate"):
        calibrated_horizon_forecast(raw, 120)


def test_recent_shock_widens_quiet_period_intervals():
    quiet = history()
    before = calibrated_horizon_forecast(quiet, 120)
    shocked = quiet.copy()
    shocked.loc[980:, "close"] *= np.exp(np.sin(np.arange(20)) * .08)
    after = calibrated_horizon_forecast(shocked, 120)
    assert (after.upper_95 - after.lower_95).iloc[0] > (before.upper_95 - before.lower_95).iloc[0]
    assert after.attrs["calibration"]["recent_daily_log_return_std"] > 0


def test_learning_rate_selection_uses_validation_only(monkeypatch):
    import component1_research as module
    from types import SimpleNamespace
    calls = []

    def fit(X_train, y_train, X_val, y_val, config):
        calls.append(config.learning_rate)
        return SimpleNamespace(rate=config.learning_rate, return_blend=1), None, None, {"val_loss": [1]}

    monkeypatch.setattr(module, "train_lstm_model", fit)
    monkeypatch.setattr(module, "predict_lstm", lambda model, X, features, target: np.full(len(X), model.rate * 1000))
    result = module.train_selected_price_model(np.zeros((2, 1, 1)), np.ones(2),
                                               np.zeros((3, 1, 1)), np.full(3, .3), module.ResearchConfig())
    assert calls == [.001, .0003]
    assert result[0].selected_learning_rate == .0003
    assert len(result[0].validation_tuning) == 2
