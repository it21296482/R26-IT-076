"""Past-only, horizon-specific forecast selection and honest holdout evidence.

The previous path used one-day weights to force structural mean reversion.
Here each candidate is tested at the actual horizon, with purged time boundaries.
Persistence is an eligible model, not something an advanced model must beat by decree.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

# Reading guide: build candidate paths -> replay historical forecasts -> select
# a candidate -> calibrate error ranges -> evaluate untouched later outcomes.
# learned_horizon.py reuses helpers here; this file also retains a simpler
# trend-based alternative. Do not present those trend paths as trained LSTMs.
# These are trading-session counts, not exact calendar-month durations.
HORIZONS = (4, 21, 60, 120)
CANDIDATES = ("persistence", "trend_20", "trend_60", "damped_20", "damped_60")


def candidate_paths(closes: np.ndarray, horizon: int) -> dict[str, np.ndarray]:
    # Persistence keeps today's price unchanged. Trend paths extend the recent
    # average log return; damped paths gradually reduce that extension so a short
    # trend is not extrapolated at full strength indefinitely.
    values = np.asarray(closes, dtype=float)
    if len(values) < 60 or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Forecasts require at least 60 finite, positive closes.")
    steps = np.arange(1, horizon + 1, dtype=float)
    last = float(values[-1])
    result = {"persistence": np.full(horizon, last)}
    for window in (20, 60):
        returns = np.diff(np.log(values[-(window + 1):]))
        # Winsorize within the observed window, never against future outcomes.
        low, high = np.quantile(returns, [0.1, 0.9])
        drift = float(np.mean(np.clip(returns, low, high)))
        # The 1% daily drift cap is a modelling safeguard, not a market price limit.
        drift = float(np.clip(drift, -0.01, 0.01))
        result[f"trend_{window}"] = last * np.exp(drift * steps)
        damped_steps = (1.0 - np.power(0.95, steps)) / (1.0 - 0.95)
        result[f"damped_{window}"] = last * np.exp(drift * damped_steps)
    return result


def horizon_observations(history: pd.DataFrame, horizon: int, stride: int = 5) -> pd.DataFrame:
    # Replay what could have been forecast at each historical origin using only
    # closes known then. Compare with the actual close `horizon` sessions later.
    # A five-session stride reduces work; overlapping horizons are still dependent.
    closes = history.close.to_numpy(dtype=float)
    rows = []
    for origin in range(60, len(closes) - horizon, stride):
        paths = candidate_paths(closes[:origin + 1], horizon)
        rows.append({
            "origin": origin, "target": origin + horizon,
            "origin_date": history.date.iloc[origin].date().isoformat(),
            "target_date": history.date.iloc[origin + horizon].date().isoformat(),
            "anchor": float(closes[origin]), "actual": float(closes[origin + horizon]),
            **{name: float(path[-1]) for name, path in paths.items()},
        })
    return pd.DataFrame(rows)


def choose_candidate(selection: pd.DataFrame) -> tuple[str, dict[str, float]]:
    # Error / origin price makes errors comparable across different price levels.
    # Selection uses historical evidence, not the later holdout test results.
    if len(selection) < 12:
        return "persistence", {}
    errors = {
        name: float(np.mean(np.abs(selection.actual - selection[name]) / selection.anchor))
        for name in CANDIDATES
    }
    selected = min(CANDIDATES, key=lambda name: errors[name])
    # Require a material improvement, rather than choosing a noisy marginal win.
    if errors[selected] >= errors["persistence"] * 0.95:
        selected = "persistence"
    return selected, errors


def residual_quantile(errors: np.ndarray, coverage: float) -> float:
    # Calibration means using completed prediction errors to set a range width.
    # Example: coverage=0.80 selects an upper rank in the sorted absolute errors.
    # The (n+1) rank adjustment is finite-sample aware; it does not guarantee that
    # 80% of future prices will fall inside the band when market conditions change.
    values = np.sort(np.asarray(errors, dtype=float))
    if not len(values):
        raise ValueError("No completed calibration observations are available.")
    rank = min(len(values), math.ceil((len(values) + 1) * coverage))
    return float(values[rank - 1])


def metrics(rows: pd.DataFrame, prediction: str) -> dict[str, float]:
    # MAE is the average absolute error in LKR; RMSE penalises large misses more;
    # MAPE expresses error as a percentage of the observed price. Lower is better.
    error = (rows.actual - rows[prediction]).to_numpy(dtype=float)
    return {
        "mae_lkr": float(np.mean(np.abs(error))),
        "rmse_lkr": float(np.sqrt(np.mean(error ** 2))),
        "mape_pct": float(np.mean(np.abs(error) / rows.actual) * 100),
    }


def fit_horizon(history: pd.DataFrame, horizon: int) -> dict:
    observations = horizon_observations(history, horizon)
    n = len(history)
    selection_end, calibration_end = int(n * 0.60), int(n * 0.80)
    # Purge crossing outcomes: a selection forecast must finish before the
    # calibration period starts, and calibration must finish before testing.
    # This prevents a long forecast's future target leaking across time splits.
    selection = observations[observations.target < selection_end]
    calibration = observations[(observations.origin >= selection_end) & (observations.target < calibration_end)]
    test = observations[observations.origin >= calibration_end]
    # Freeze the selected candidate before measuring its later test accuracy.
    frozen_name, errors = choose_candidate(selection)
    evaluation = {"status": "insufficient_purged_observations", "observations": int(len(test))}
    if len(calibration) >= 12 and len(test) >= 12:
        q95 = residual_quantile(np.abs(calibration.actual - calibration[frozen_name]) / calibration.anchor, 0.95)
        selected_metrics, baseline_metrics = metrics(test, frozen_name), metrics(test, "persistence")
        evaluation = {
            "status": "retrospective_purged_holdout",
            "selected_candidate": frozen_name, "observations": int(len(test)),
            "selection_end_date": history.date.iloc[selection_end - 1].date().isoformat(),
            "calibration_end_date": history.date.iloc[calibration_end - 1].date().isoformat(),
            "test_start_date": test.origin_date.iloc[0],
            "selected": selected_metrics, "baseline": baseline_metrics,
            "beats_baseline_mae": selected_metrics["mae_lkr"] < baseline_metrics["mae_lkr"],
            "interval_95_coverage": float((np.abs(test.actual - test[frozen_name]) / test.anchor <= q95).mean()),
        }

    # A live refit can use all completed past outcomes, but is never its own test.
    live_boundary = n - 252
    live_selection = observations[(observations.target < live_boundary) & (observations.origin >= max(60, n - 1260))]
    live_calibration = observations[observations.origin >= live_boundary]
    live_name, live_errors = choose_candidate(live_selection)
    if len(live_calibration) < 12:
        live_name = "persistence"
        live_calibration = observations.tail(50)
    if live_calibration.empty:
        raise ValueError(f"Insufficient history to calibrate a {horizon}-session forecast.")
    # Store errors relative to the origin price; forecast assembly converts these
    # proportions back into LKR widths around the current forecast path.
    relative_errors = np.abs(live_calibration.actual - live_calibration[live_name]) / live_calibration.anchor
    return {
        "horizon": horizon, "live_candidate": live_name,
        "live_selection_errors": live_errors, "frozen_selection_errors": errors,
        "calibration_observations": int(len(live_calibration)),
        "calibration_latest_target": live_calibration.target_date.iloc[-1],
        "q80": residual_quantile(relative_errors, 0.80),
        "q95": residual_quantile(relative_errors, 0.95),
        "holdout": evaluation,
    }


def calibrated_horizon_forecast(raw_df: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    # Choose/calibrate each horizon separately: a good four-day method need not
    # be a good six-month method. This alternative selects simple candidate paths.
    history = raw_df[["date", "close"]].copy().sort_values("date").reset_index(drop=True)
    history["date"] = pd.to_datetime(history.date)
    if history.date.duplicated().any():
        raise ValueError("Duplicate trading dates cannot be used for horizon calibration.")
    horizons = sorted(set((1, *[h for h in HORIZONS if h <= horizon_days], horizon_days)))
    fits = {h: fit_horizon(history, h) for h in horizons}
    closes = history.close.to_numpy(dtype=float)
    paths = candidate_paths(closes, horizon_days)
    points, q80, q95 = [], [], []
    for h in horizons:
        fit = fits[h]
        points.append(float(paths[fit["live_candidate"]][h - 1]))
        q80.append(float(fit["q80"]))
        q95.append(float(fit["q95"]))
    steps = np.arange(1, horizon_days + 1)
    # Lines between horizon checkpoints are interpolated for chart continuity;
    # they are not independently trained predictions for every intervening day.
    estimates = np.interp(steps, horizons, points)
    recent_returns = np.diff(np.log(closes[-61:]))
    recent_sigma = float(np.std(recent_returns, ddof=0))
    # A newly volatile regime should not retain a narrow quiet-period band.
    q80 = np.maximum(q80, 1.2816 * recent_sigma * np.sqrt(horizons))
    q95 = np.maximum(q95, 1.96 * recent_sigma * np.sqrt(horizons))
    # Keep bands nested and nondecreasing; they are empirical, not guarantees.
    width80 = closes[-1] * np.interp(steps, horizons, np.maximum.accumulate(q80))
    width95 = closes[-1] * np.interp(steps, horizons, np.maximum.accumulate(np.maximum(q95, q80)))
    # BDay removes weekends only; target dates do not incorporate CSE holidays.
    # Lower/upper ranges show uncertainty, not guaranteed best/worst outcomes.
    forecast = pd.DataFrame({
        "date": pd.bdate_range(history.date.iloc[-1] + BDay(1), periods=horizon_days),
        "forecast_step": steps,
        "predicted_close": estimates, "ensemble_predicted_close": estimates,
        "naive_random_walk_close": closes[-1],
        "moving_average_drift_close": paths["damped_20"],
        # Legacy column retained as a candidate path, NOT advertised as LSTM output.
        "scenario_lstm_close": estimates, "fair_value_anchor": closes[-1],
        "lower_80": np.maximum(0.01, estimates - width80), "upper_80": estimates + width80,
        "lower_95": np.maximum(0.01, estimates - width95), "upper_95": estimates + width95,
    })
    forecast.attrs["calibration"] = {
        "method": "horizon_specific_purged_selection_and_completed_outcome_refit",
        "recent_daily_log_return_std": recent_sigma,
        "interval_basis": "Horizon residual quantiles with a recent-volatility floor; no coverage guarantee",
        "horizons": {str(h): fit for h, fit in fits.items()},
        "limitations": [
            "Holdout results are retrospective, not a new prospective six-month experiment.",
            "Overlapping forecast origins are dependent; empirical bands have no guaranteed coverage under market shifts.",
            "Intermediate path points interpolate calibrated checkpoints; business dates are not an official CSE holiday calendar.",
            "Historical prices must be checked for splits and corporate actions; an external event is not a proven cause.",
        ],
    }
    return forecast
