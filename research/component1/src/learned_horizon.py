"""Direct multi-session return regressions with purged, chronological evaluation.

The central path is a learned estimate, not a persistence substitute. Baseline
performance is reported honestly even when it outperforms the learned model.
No test observations select parameters, and no cached forecasts are loaded.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from threadpoolctl import threadpool_limits

try:
    from .horizon_forecast import HORIZONS, candidate_paths, metrics, residual_quantile
    from .runtime_progress import report_progress
except ImportError:
    from horizon_forecast import HORIZONS, candidate_paths, metrics, residual_quantile
    from runtime_progress import report_progress


def feature_frame(history):
    # Describe the market at each forecast origin using information available
    # by that close: momentum (direction), volatility (variability), distance
    # from moving averages, drawdown, relative volume and the daily price range.
    close = history.close.astype(float)
    returns = np.log(close).diff()
    features = pd.DataFrame(index=history.index)
    for window in (4, 10, 20, 60):
        features[f"momentum_{window}"] = np.log(close / close.shift(window))
        features[f"volatility_{window}"] = returns.rolling(window).std(ddof=0)
        features[f"mean_gap_{window}"] = close / close.rolling(window).mean() - 1
    features["drawdown_60"] = close / close.rolling(60).max() - 1
    if "volume" in history:
        volume = history.volume.astype(float)
        features["relative_volume"] = np.log1p(volume / volume.rolling(20).median().clip(lower=1))
    if {"high", "low"}.issubset(history.columns):
        features["range"] = (history.high - history.low) / close
    return features.replace([np.inf, -np.inf], np.nan)


# Compare an unchanged-price baseline with learned models for EACH horizon.
# The winning model can differ between stocks, horizons and refreshed datasets.
CANDIDATES = ("persistence", "ridge_1", "ridge_10", "ridge_100", "ridge_1000",
              "random_forest", "extra_trees", "gradient_boosting")


def new_model(name):
    # These settings define new estimators; .fit() learns their parameters later.
    if name.startswith("ridge_"):
        # Scale features first. Alpha (1, 10, 100 or 1000) controls how strongly
        # large regression coefficients are penalised; larger means more shrinkage.
        return make_pipeline(StandardScaler(), Ridge(alpha=float(name.split("_")[1])))
    if name == "random_forest":
        # 96 trees vote by averaging. Depth 6 and at least 8 rows per leaf limit
        # overfitting; each split considers 80% of the input features.
        return RandomForestRegressor(n_estimators=96, max_depth=6, min_samples_leaf=8,
                                     max_features=.8, random_state=42, n_jobs=1)
    if name == "extra_trees":
        # More randomised trees; depth and minimum leaf size limit complexity.
        return ExtraTreesRegressor(n_estimators=96, max_depth=8, min_samples_leaf=8,
                                   random_state=42, n_jobs=1)
    if name == "gradient_boosting":
        # Up to 120 boosting rounds with small updates (0.05). Shallow trees,
        # minimum leaf size and L2 penalties constrain the fitted relationships.
        return HistGradientBoostingRegressor(max_iter=120, max_depth=3, min_samples_leaf=12,
                                            learning_rate=.05, l2_regularization=10.,
                                            early_stopping=False, random_state=42)
    raise ValueError(f"Unknown forecast candidate: {name}")


def candidate_prediction(name, train_x, train_y, predict_x, anchors):
    if name == "persistence":
        return np.asarray(anchors, dtype=float)
    with threadpool_limits(limits=1):
        # Fit from scratch on the supplied training split. No saved estimator is
        # loaded here; predictions convert learned log returns back to LKR prices.
        model = new_model(name).fit(train_x, train_y)
        return anchors * np.exp(np.clip(model.predict(predict_x), -2, 2))


def select_candidate(x, y, anchor, actual, training, tuning):
    # Fit on training rows and compare on separate tuning rows. The lowest mean
    # absolute price error / origin price wins, including persistence if best.
    errors = {}
    for name in CANDIDATES:
        prediction = candidate_prediction(name, x[training], y[training], x[tuning], anchor[tuning])
        errors[name] = float(np.mean(np.abs(prediction - actual[tuning]) / anchor[tuning]))
    return min(errors, key=errors.get), errors


def fit_direct_horizon(history, features, horizon):
    # An origin is the day a forecast would have been made; its target is the
    # observed close `horizon` sessions later. Purging prevents training outcomes
    # from extending into the next evaluation period and leaking future prices.
    n = len(history)
    origins = np.arange(60, n - horizon, 5)
    origins = origins[features.iloc[origins].notna().all(axis=1).to_numpy()]
    if len(origins) < 40:
        raise ValueError(f"Not enough completed historical outcomes to train a {horizon}-session regression.")
    x = features.iloc[origins].to_numpy()
    anchor = history.close.iloc[origins].to_numpy(dtype=float)
    actual = history.close.iloc[origins + horizon].to_numpy(dtype=float)
    targets = origins + horizon
    # The target is the return over this exact horizon, not tomorrow's return
    # repeatedly reused for six months. exp(predicted return) restores price units.
    y = np.log(actual / anchor)
    tuning_start, selection_end, calibration_end = int(n * .45), int(n * .60), int(n * .80)
    # These chronological masks keep completed targets out of later periods:
    # early training -> tuning before 60% -> calibration before 80% -> final test.
    training = targets < tuning_start
    tuning = (origins >= tuning_start) & (targets < selection_end)
    selection = targets < selection_end
    calibration = (origins >= selection_end) & (targets < calibration_end)
    test = origins >= calibration_end
    if training.sum() < 12 or tuning.sum() < 5:
        raise ValueError(f"Insufficient purged training and tuning history for {horizon} sessions.")
    frozen_name, tuning_errors = select_candidate(x, y, anchor, actual, training, tuning)
    evaluation = {"status": "insufficient_purged_observations", "observations": int(test.sum())}
    if calibration.sum() >= 12 and test.sum() >= 12:
        calibration_predictions = candidate_prediction(frozen_name, x[selection], y[selection], x[calibration], anchor[calibration])
        # Use separate calibration misses to estimate uncertainty. Test prices
        # measure accuracy/coverage afterwards; they do not choose these widths.
        calibration_errors = np.abs(actual[calibration] - calibration_predictions) / anchor[calibration]
        predicted = candidate_prediction(frozen_name, x[selection], y[selection], x[test], anchor[test])
        rows = pd.DataFrame({"actual": actual[test], "regression": predicted, "persistence": anchor[test]})
        selected, baseline = metrics(rows, "regression"), metrics(rows, "persistence")
        evaluation = {
            "status": "retrospective_purged_holdout", "selected_candidate": frozen_name,
            "observations": int(test.sum()), "selected": selected, "baseline": baseline,
            "beats_baseline_mae": selected["mae_lkr"] < baseline["mae_lkr"],
            "training_latest_target": history.date.iloc[targets[selection].max()].date().isoformat(),
            "calibration_first_origin": history.date.iloc[origins[calibration].min()].date().isoformat(),
            "calibration_latest_target": history.date.iloc[targets[calibration].max()].date().isoformat(),
            "test_start_date": history.date.iloc[origins[test].min()].date().isoformat(),
            "interval_95_coverage": float(np.mean(np.abs(actual[test] - predicted) / anchor[test] <= residual_quantile(calibration_errors, .95))),
        }
    # Recent completed outcomes calibrate intervals without reusing fitted targets.
    boundary = n - max(252, horizon + 90)
    live_train = targets < boundary
    live_calibration = origins >= boundary
    if live_train.sum() < 12 or live_calibration.sum() < 12:
        raise ValueError(f"Insufficient independent interval calibration for {horizon} sessions.")
    recent_tuning_start = boundary - max(180, horizon + 60)
    recent_training = targets < recent_tuning_start
    recent_tuning = (origins >= recent_tuning_start) & (targets < boundary)
    if recent_training.sum() < 12 or recent_tuning.sum() < 5:
        raise ValueError(f"Insufficient recent purged model selection for {horizon} sessions.")
    # The latest forecast reselects a candidate from more recent completed data.
    # If it differs from the frozen holdout winner, the earlier holdout score is
    # not an independent accuracy claim for this newly selected live model.
    live_name, live_errors = select_candidate(x, y, anchor, actual, recent_training, recent_tuning)
    predicted = candidate_prediction(live_name, x[live_train], y[live_train], x[live_calibration], anchor[live_calibration])
    residuals = np.abs(actual[live_calibration] - predicted) / anchor[live_calibration]
    # Refit from scratch on every available completed target after evaluation.
    last_features = features.iloc[[-1]].to_numpy()
    estimate = float(candidate_prediction(live_name, x, y, last_features, np.array([history.close.iloc[-1]]))[0])
    return {
        "horizon": horizon, "live_candidate": live_name, "estimate": estimate,
        "alpha": float(frozen_name.split("_")[1]) if frozen_name.startswith("ridge_") else None,
        "tuning_errors": tuning_errors, "live_selection_errors": live_errors,
        "selection_metric": "mean absolute price error divided by the origin price",
        "selection_training_latest_target": history.date.iloc[targets[recent_training].max()].date().isoformat(),
        "selection_tuning_first_origin": history.date.iloc[origins[recent_tuning].min()].date().isoformat(),
        "selection_tuning_latest_target": history.date.iloc[targets[recent_tuning].max()].date().isoformat(),
        "live_calibration_first_origin": history.date.iloc[origins[live_calibration].min()].date().isoformat(),
        "evaluation_matches_live_model": frozen_name == live_name,
        "training_observations": int(len(origins)),
        "latest_training_target": history.date.iloc[targets.max()].date().isoformat(),
        "calibration_observations": int(live_calibration.sum()),
        "q80": residual_quantile(residuals, .8), "q95": residual_quantile(residuals, .95),
        "holdout": evaluation,
    }


def learned_horizon_forecast(raw_df, horizon_days):
    # Main app forecast path: independently select/freshly fit a model for each
    # requested horizon, then assemble their central estimates and uncertainty.
    history = raw_df.copy().sort_values("date").reset_index(drop=True)
    history["date"] = pd.to_datetime(history.date)
    if history.date.duplicated().any():
        raise ValueError("Duplicate trading dates cannot train a forecast.")
    closes = history.close.to_numpy(dtype=float)
    paths = candidate_paths(closes, horizon_days)
    features = feature_frame(history)
    horizons = sorted(set((*[h for h in HORIZONS if h <= horizon_days], horizon_days)))
    fits = {}
    for index, horizon in enumerate(horizons):
        fits[horizon] = fit_direct_horizon(history, features, horizon)
        report_progress("forecast_training", 72 + index * 5, horizon=horizon,
                        selected_candidate=fits[horizon]["live_candidate"],
                        candidates_compared=len(fits[horizon]["live_selection_errors"]))
    steps = np.arange(1, horizon_days + 1)
    # Interpolate only the chart between trained horizon endpoints. Intermediate
    # points are not additional independent models or verified recovery targets.
    estimates = np.interp(steps, [0, *horizons], [closes[-1], *[fits[h]["estimate"] for h in horizons]])
    sigma = float(np.std(np.diff(np.log(closes[-61:]))))
    # Take the larger of calibrated past errors and a recent-volatility floor.
    # This avoids a narrow quiet-period band after volatility rises. Approximate
    # normal z-values support the floor; they do not prove normal market returns.
    # maximum.accumulate prevents longer-horizon widths shrinking below earlier ones.
    q80 = np.maximum.accumulate([max(fits[h]["q80"], 1.2816 * sigma * np.sqrt(h)) for h in horizons])
    q95 = np.maximum.accumulate([max(fits[h]["q95"], q80[i], 1.96 * sigma * np.sqrt(h)) for i,h in enumerate(horizons)])
    width80 = closes[-1] * np.interp(steps, [0, *horizons], [0, *q80])
    width95 = closes[-1] * np.interp(steps, [0, *horizons], [0, *q95])
    # Compatibility column names remain for callers: scenario_lstm_close is NOT
    # evidence that an LSTM produced this horizon path; fair_value_anchor is just
    # the latest close, not a fundamental fair-value valuation.
    forecast = pd.DataFrame({
        "date": pd.bdate_range(history.date.iloc[-1] + pd.offsets.BDay(1), periods=horizon_days),
        "forecast_step": steps, "predicted_close": estimates, "ensemble_predicted_close": estimates,
        "naive_random_walk_close": closes[-1], "moving_average_drift_close": paths["damped_20"],
        "scenario_lstm_close": estimates, "fair_value_anchor": closes[-1],
        "lower_80": np.maximum(.01, estimates-width80), "upper_80": estimates+width80,
        "lower_95": np.maximum(.01, estimates-width95), "upper_95": estimates+width95,
    })
    forecast.attrs["calibration"] = {
        "method": "fresh_purged_per_horizon_model_selection", "horizons": {str(h):fit for h,fit in fits.items()},
        "interval_basis": "Independent completed-outcome residuals with a recent-volatility floor.",
        "limitations": ["The best candidate is selected from a bounded candidate set, not all possible models; future accuracy is unknown.",
                        "A persistence forecast is used when it wins recent validation, not relabelled as a learned price change.",
                        "Historical holdout scores evaluate an earlier frozen selection policy; a different live winner has no independent prospective validation.",
                        "Trading-day dates exclude weekends but do not model the official CSE holiday calendar.",
                        "Intervals are empirical, not guaranteed prices or investment advice."],
    }
    return forecast
