"""Reproducible experiments for the Component 1 IEEE paper (revision 2).

Run from research/component1:
    python experiments/paper_experiments.py --stocks JKH BIL

Any CSE symbol works if data/actuals/<CODE>_actual_through_<date>.csv (or a
CSV passed with --csv CODE=path) has date, open, high, low, close, volume.

Experiments
-----------
A  Leakage-free one-step evaluation with ablations.
   Proxy labels use past-only rolling quantiles (current pipeline). Every
   detector is tuned on the chronological validation split only (F0.5), then
   frozen and scored on the test split. 95% CIs use a moving-block bootstrap.
B  Walk-forward deviation-pattern evaluation on independently documented
   CSE stress episodes (2019 Easter attacks, 2020 COVID-19 closure, 2022
   sovereign crisis). The expected-price model is refit every calendar year on
   data before that year. Detector thresholds are fixed on 2016-2018 residuals
   to an equal false-alarm budget, without any episode label.
C  Diebold-Mariano comparison of the preserved three-month paths with
   persistence.
D  Deviation-pattern profiles per stock and episode, plus the unlabelled
   May-August 2026 case study.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

import component1_research as cr  # noqa: E402

sys.path.insert(0, str(HERE))

OUT = ROOT / "artifacts" / "paper_v3_verified"
EPISODES = [
    # Anchors documented in contemporaneous reports; windows follow the
    # pipeline's EVENT_WINDOWS. Detection is scored only inside them.
    {"id": "E1", "name": "Easter attacks", "start": "2019-04-22", "end": "2019-05-10"},
    {"id": "E2", "name": "COVID-19 closure", "start": "2020-03-09", "end": "2020-05-15"},
    {"id": "E3", "name": "Sovereign crisis", "start": "2022-03-01", "end": "2022-07-31"},
]
CALIBRATION = ("2016-01-01", "2018-12-31")
EVALUATION = ("2019-01-01", "2026-08-28")
CASE_WINDOW = ("2026-05-08", "2026-08-28")
ALARM_BUDGET = 0.02          # share of calibration days allowed to alarm
CUSUM_K = 0.5                # reference value in robust-z units
ROBUST_WINDOW = 252
BOOT_REPS = 2000
BOOT_BLOCK = 20
SEED = 42


# --------------------------------------------------------------------- data
DATA_DIR = ROOT / "data" / "actuals"


def load_history(code: str, override: dict[str, str]) -> pd.DataFrame:
    path = Path(override[code]) if code in override else sorted(DATA_DIR.glob(f"{code}_actual_through_*.csv"))[-1]
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def config_for(code: str) -> cr.ResearchConfig:
    return replace(cr.ResearchConfig(), stock_code=code, random_seed=SEED)


def fit_expected_price(model_df: pd.DataFrame, fit_rows: np.ndarray, config: cr.ResearchConfig):
    """Fit on fit_rows (boolean mask over sequences) using its last 12.5% as validation."""
    X, y, rows = cr.create_sequences(model_df, feature_columns=cr.DEFAULT_FEATURE_COLUMNS, lookback=config.lookback)
    return X, y, rows


def residual_frame(rows: pd.DataFrame, pred: np.ndarray, y: np.ndarray, config, bands=None):
    frame = rows.copy()
    frame["predicted_price"] = pred
    frame["actual_price"] = y
    frame["naive_baseline_predicted_price"] = pd.to_numeric(rows["prev_close"], errors="coerce").to_numpy()
    kw = {} if bands is None else {"downside_band": bands["downside_band"], "upside_band": bands["upside_band"]}
    return cr.add_anomaly_columns(frame, volume_scale=config.volume_scale, epsilon=config.liquidity_epsilon, **kw)


def robust_scale(past: pd.Series, window: int, min_periods: int) -> tuple[pd.Series, pd.Series]:
    """Past-only location and scale. MAD is floored by the mean absolute deviation
    so tick-constrained stocks (many exactly-zero returns) keep a usable scale."""
    med = past.rolling(window, min_periods=min_periods).median()
    # Centre every member of a window on THAT window's location. A second
    # rolling average of differently centred deviations is not its MAD/MeanAD.
    mad = 1.4826 * past.rolling(window, min_periods=min_periods).apply(
        lambda x: np.nanmedian(np.abs(x - np.nanmedian(x))), raw=True)
    mean_ad = 1.2533 * past.rolling(window, min_periods=min_periods).apply(
        lambda x: np.nanmean(np.abs(x - np.nanmean(x))), raw=True)
    return med, np.maximum(np.maximum(mad, mean_ad), 1e-6)


def robust_z(signed: pd.Series, window: int = ROBUST_WINDOW, min_periods: int = 60) -> pd.Series:
    """Past-only robust standardisation of relative residuals."""
    med, scale = robust_scale(signed.shift(1), window, min_periods)
    return (signed - med) / scale


def cusum(z: pd.Series, k: float, h: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Two-sided CUSUM with reset after alarm. Returns (C+, C-, alarm)."""
    cp = cm = 0.0
    out_p, out_m, alarm = [], [], []
    for value in z.fillna(0.0).to_numpy():
        cp = max(0.0, cp + value - k)
        cm = max(0.0, cm - value - k)
        hit = cp >= h or cm >= h
        out_p.append(cp)
        out_m.append(cm)
        alarm.append(hit)
        if hit:
            cp = cm = 0.0
    idx = z.index
    return pd.Series(out_p, idx), pd.Series(out_m, idx), pd.Series(alarm, idx)


def cusum_level(z: pd.Series, k: float) -> pd.Series:
    """Max of the two CUSUM statistics without reset (for threshold calibration)."""
    cp = cm = 0.0
    out = []
    for value in z.fillna(0.0).to_numpy():
        cp = max(0.0, cp + value - k)
        cm = max(0.0, cm - value - k)
        out.append(max(cp, cm))
    return pd.Series(out, z.index)


# ---------------------------------------------------------------- metrics
def prf(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    tp = int(((y == 1) & (p == 1)).sum()); fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum()); tn = int(((y == 0) & (p == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
    f05 = (1.25 * precision * recall / (0.25 * precision + recall)) if (precision + recall) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1, "f05": f05,
            "fpr": fp / (fp + tn) if fp + tn else 0.0, "alarm_rate": float(p.mean()) if len(p) else 0.0}


def block_bootstrap_ci(y: np.ndarray, p: np.ndarray, metric: str = "f1", reps: int = BOOT_REPS,
                       block: int = BOOT_BLOCK, seed: int = SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(y)
    if n == 0:
        return float("nan"), float("nan")
    block = min(block, n)
    starts_max = max(1, n - block + 1)
    vals = []
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, starts_max, size=math.ceil(n / block))])[:n]
        vals.append(prf(y[idx], p[idx])[metric])
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def tune_threshold(score_val: np.ndarray, y_val: np.ndarray, valid: np.ndarray | None = None,
                   qs=np.linspace(0.60, 0.995, 80), extra=()) -> float:
    s = score_val[np.isfinite(score_val) & (valid if valid is not None else True)]
    candidates = np.unique(np.concatenate([np.quantile(s, qs), np.asarray(extra, dtype=float)]))
    best, best_key = candidates[-1], (-1.0, -1.0)
    for t in candidates:
        pred = (score_val >= t) & (valid if valid is not None else True)
        m = prf(y_val, pred.astype(int))
        key = (m["f05"], m["precision"])
        if key > best_key:
            best, best_key = t, key
    return float(best)


# -------------------------------------------------------------- experiment A
def experiment_a(code: str, raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    config = config_for(code)
    cr.set_random_seed(SEED)
    eng = cr.engineer_features(raw)
    model_df = cr.prepare_model_frame(eng, feature_columns=cr.DEFAULT_FEATURE_COLUMNS)
    X, y, rows = cr.create_sequences(model_df, feature_columns=cr.DEFAULT_FEATURE_COLUMNS, lookback=config.lookback)
    tr_end, va_end = cr.split_indices(len(X), config.test_fraction, config.val_fraction)
    model, fs, ts, _ = cr.train_selected_price_model(X[:tr_end], y[:tr_end], X[tr_end:va_end], y[tr_end:va_end], config)
    preds = {s: cr.predict_lstm(model, X[a:b], fs, ts) for s, (a, b) in
             {"train": (0, tr_end), "val": (tr_end, va_end), "test": (va_end, len(X))}.items()}
    frames = {s: residual_frame(rows.iloc[a:b].reset_index(drop=True), preds[s], y[a:b], config) for s, (a, b) in
              {"train": (0, tr_end), "val": (tr_end, va_end), "test": (va_end, len(X))}.items()}
    bands = cr.calibrate_prediction_bands(frames["train"], frames["val"], config)
    frames = {s: residual_frame(rows.iloc[a:b].reset_index(drop=True), preds[s], y[a:b], config, bands) for s, (a, b) in
              {"train": (0, tr_end), "val": (tr_end, va_end), "test": (va_end, len(X))}.items()}
    cal = cr.calibrate_final_anomaly_logic(frames["train"], frames["val"], config)
    val_fixed = cr.add_anomaly_columns(frames["val"], config.volume_scale, config.liquidity_epsilon,
                                       bands["downside_band"], bands["upside_band"], 0.0,
                                       cal["liquidity_threshold"], cal["prediction_band_threshold"])
    test_adapt = cr.apply_causal_anomaly_thresholds(pd.concat([frames["train"], val_fixed], ignore_index=True),
                                                    frames["test"], cal["liquidity_threshold"],
                                                    cal["prediction_band_threshold"], config.adaptive_anomaly_window)

    # Robust relative-residual z over the whole chronology, past-only.
    whole = pd.concat([frames["train"], frames["val"], frames["test"]], ignore_index=True)
    whole["rel_resid"] = whole["signed_residual"] / whole["predicted_price"]
    whole["rz"] = robust_z(whole["rel_resid"])
    n_tr, n_va = len(frames["train"]), len(frames["val"])
    rz_val = whole["rz"].iloc[n_tr:n_tr + n_va].to_numpy()
    rz_test = whole["rz"].iloc[n_tr + n_va:].to_numpy()
    lvl = cusum_level(whole["rz"], CUSUM_K)

    yv = frames["val"]["proxy_anomaly_label"].astype(int).to_numpy()
    yt = frames["test"]["proxy_anomaly_label"].astype(int).to_numpy()
    validv = ~frames["val"]["zero_volume_flag"].to_numpy(bool)
    validt = ~frames["test"]["zero_volume_flag"].to_numpy(bool)
    liq_v = frames["val"]["liquidity_aware_anomaly_score"].to_numpy(float)
    liq_t = frames["test"]["liquidity_aware_anomaly_score"].to_numpy(float)
    band_v = frames["val"]["prediction_band_severity"].to_numpy(float)
    band_t = frames["test"]["prediction_band_severity"].to_numpy(float)
    dev_v = frames["val"]["deviation"].to_numpy(float)
    dev_t = frames["test"]["deviation"].to_numpy(float)

    results: dict[str, np.ndarray] = {}
    results["Proposed: score OR band (past-only adaptive)"] = test_adapt["final_anomaly_detected"].to_numpy(int)
    t = tune_threshold(liq_v, yv, validv)
    results["Ablation: volume-scaled score only"] = ((liq_t >= t) & validt).astype(int)
    t = tune_threshold(band_v, yv, qs=np.linspace(0.80, 0.995, 80), extra=(1.05,))
    results["Ablation: band severity only"] = (band_t >= max(t, 1.05)).astype(int)
    t = tune_threshold(dev_v, yv)
    results["Ablation: unscaled |residual|"] = (dev_t >= t).astype(int)
    t = tune_threshold(np.abs(rz_val), yv)
    results["Ablation: robust residual z (MAD)"] = (np.abs(rz_test) >= t).astype(int)

    # Original baselines, identical to the pipeline definitions.
    tr = frames["train"]
    mu, sd = tr["return_1d"].mean(), tr["return_1d"].std(ddof=0) or 1.0
    zthr = max(3.0, float(((tr["return_1d"] - mu) / sd).abs().quantile(config.anomaly_quantile)))
    results["Baseline: return Z-score"] = (((frames["test"]["return_1d"] - mu) / sd).abs() >= zthr).astype(int).to_numpy()
    sc = StandardScaler().fit(tr[cr.DEFAULT_FEATURE_COLUMNS])
    iso = IsolationForest(contamination=config.isolation_forest_contamination, random_state=SEED).fit(sc.transform(tr[cr.DEFAULT_FEATURE_COLUMNS]))
    ithr = float(np.quantile(-iso.score_samples(sc.transform(tr[cr.DEFAULT_FEATURE_COLUMNS])), config.anomaly_quantile))
    results["Baseline: Isolation Forest"] = (-iso.score_samples(sc.transform(frames["test"][cr.DEFAULT_FEATURE_COLUMNS])) >= ithr).astype(int)
    results["Reference: always normal"] = np.zeros_like(yt)

    rows_out = []
    for name, p in results.items():
        m = prf(yt, p)
        lo, hi = block_bootstrap_ci(yt, p, "f1")
        rows_out.append({"stock": code, "detector": name, **m, "f1_ci_low": lo, "f1_ci_high": hi})
    table = pd.DataFrame(rows_out)
    meta = {
        "stock": code, "sequences": int(len(X)), "train": int(tr_end), "validation": int(va_end - tr_end),
        "test": int(len(X) - va_end),
        "test_start": str(frames["test"]["date"].iloc[0].date()), "test_end": str(frames["test"]["date"].iloc[-1].date()),
        "validation_positives": int(yv.sum()), "test_positives": int(yt.sum()),
        "return_blend": float(getattr(model, "return_blend", float("nan"))),
        "learning_rate": float(getattr(model, "selected_learning_rate", float("nan"))),
        "test_mae_model": float(np.mean(np.abs(frames["test"]["deviation"]))),
        "test_mae_persistence": float(np.mean(np.abs(frames["test"]["actual_price"] - frames["test"]["naive_baseline_predicted_price"]))),
        "liquidity_threshold": cal["liquidity_threshold"], "band_threshold": cal["prediction_band_threshold"],
    }
    return table, meta


# -------------------------------------------------------------- experiment B
def walk_forward_residuals(code: str, raw: pd.DataFrame) -> pd.DataFrame:
    config = config_for(code)
    eng = cr.engineer_features(raw)
    model_df = cr.prepare_model_frame(eng, feature_columns=cr.DEFAULT_FEATURE_COLUMNS)
    X, y, rows = cr.create_sequences(model_df, feature_columns=cr.DEFAULT_FEATURE_COLUMNS, lookback=config.lookback)
    dates = pd.to_datetime(rows["date"]).reset_index(drop=True)
    parts, blends = [], []
    for year in range(2016, 2027):
        fit_mask = (dates < pd.Timestamp(f"{year}-01-01")).to_numpy()
        pred_mask = (dates.dt.year == year).to_numpy()
        if fit_mask.sum() < 500 or pred_mask.sum() == 0:
            continue
        idx = np.where(fit_mask)[0]
        cut = idx[int(len(idx) * 0.875)]
        cr.set_random_seed(SEED)
        model, fs, ts, _ = cr.train_selected_price_model(X[:cut], y[:cut], X[cut:idx[-1] + 1], y[cut:idx[-1] + 1], config)
        p = cr.predict_lstm(model, X[pred_mask], fs, ts)
        part = residual_frame(rows[pred_mask].reset_index(drop=True), p, y[pred_mask], config)
        part["fit_year"] = year
        part["return_blend"] = float(getattr(model, "return_blend", np.nan))
        parts.append(part)
        blends.append({"stock": code, "year": year, "return_blend": part["return_blend"].iloc[0],
                       "learning_rate": float(getattr(model, "selected_learning_rate", np.nan))})
        print(f"  {code} {year}: blend={part['return_blend'].iloc[0]} n={len(part)}", flush=True)
    wf = pd.concat(parts, ignore_index=True)
    wf["date"] = pd.to_datetime(wf["date"])
    wf["rel_resid"] = wf["signed_residual"] / wf["predicted_price"]
    wf["rz"] = robust_z(wf["rel_resid"])
    wf["abs_return"] = wf["return_1d"].abs()
    wf.attrs["blends"] = blends
    return wf


def in_window(dates: pd.Series, start: str, end: str) -> pd.Series:
    return dates.between(pd.Timestamp(start), pd.Timestamp(end))


def experiment_b(code: str, wf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = wf["date"]
    cal = in_window(d, *CALIBRATION)
    q = 1.0 - ALARM_BUDGET
    valid = ~wf["zero_volume_flag"]

    # Past-only rolling standardisation of the liquidity score and |return|.
    def rolling_pct(s: pd.Series) -> pd.Series:
        med, scale = robust_scale(s.shift(1), ROBUST_WINDOW, 60)
        return (s - med) / scale

    def rolling_z(s: pd.Series) -> pd.Series:
        past = s.shift(1)
        mu = past.rolling(ROBUST_WINDOW, min_periods=60).mean()
        sd = past.rolling(ROBUST_WINDOW, min_periods=60).std()
        return (s - mu) / sd.replace(0, np.nan)

    scores = {
        "Daily: return Z-score": rolling_z(wf["return_1d"]).abs(),
        "Daily: volume-scaled score": rolling_pct(np.log1p(wf["liquidity_aware_anomaly_score"].where(valid))),
        "Daily: robust residual z": wf["rz"].abs(),
    }
    alarms = {}
    thresholds = {}
    for name, s in scores.items():
        t = float(s[cal].quantile(q))
        thresholds[name] = t
        alarms[name] = (s >= t).fillna(False)
    # Proposed daily rule: OR of the volume score and the residual band, each given half the budget.
    t_liq = float(scores["Daily: volume-scaled score"][cal].quantile(1 - ALARM_BUDGET / 2))
    t_rz = float(scores["Daily: robust residual z"][cal].quantile(1 - ALARM_BUDGET / 2))
    alarms["Daily: proposed score OR band"] = ((scores["Daily: volume-scaled score"] >= t_liq) | (scores["Daily: robust residual z"] >= t_rz)).fillna(False)
    thresholds["Daily: proposed score OR band"] = float("nan")

    # Pattern monitors on the robust residual z.
    lvl = cusum_level(wf["rz"], CUSUM_K)
    # choose h so that reset-CUSUM alarms on <= budget of calibration days
    h_grid = np.linspace(1.0, 20.0, 191)
    h_sel = h_grid[-1]
    for h in h_grid:
        _, _, a = cusum(wf["rz"], CUSUM_K, h)
        if a[cal].mean() <= ALARM_BUDGET:
            h_sel = h
            break
    cp, cm, a = cusum(wf["rz"], CUSUM_K, h_sel)
    alarms["Pattern: two-sided CUSUM"] = a
    thresholds["Pattern: two-sided CUSUM"] = float(h_sel)
    ew = wf["rz"].fillna(0.0).ewm(alpha=0.2, adjust=False).mean()
    t_ew = float(ew.abs()[cal].quantile(q))
    alarms["Pattern: EWMA residual"] = ew.abs() >= t_ew
    thresholds["Pattern: EWMA residual"] = t_ew

    ev = in_window(d, *EVALUATION)
    episode_mask = pd.Series(False, index=wf.index)
    for e in EPISODES:
        episode_mask |= in_window(d, e["start"], e["end"])
    rows = []
    for name, a in alarms.items():
        row = {"stock": code, "detector": name, "threshold": thresholds[name],
               "calibration_alarm_rate": float(a[cal].mean())}
        hits = 0
        for e in EPISODES:
            w = in_window(d, e["start"], e["end"])
            first = np.where(a[w].to_numpy())[0]
            row[f"{e['id']}_detected"] = bool(len(first))
            row[f"{e['id']}_delay_days"] = int(first[0]) if len(first) else np.nan
            row[f"{e['id']}_alarm_days"] = int(a[w].sum())
            row[f"{e['id']}_trading_days"] = int(w.sum())
            hits += bool(len(first))
        outside = ev & ~episode_mask
        row["episodes_detected"] = hits
        row["false_alarms_per_100_days"] = float(100 * a[outside].mean())
        row["outside_days"] = int(outside.sum())
        rows.append(row)
    summary = pd.DataFrame(rows)
    wf = wf.assign(cusum_plus=cp, cusum_minus=cm,
                   cusum_alarm=alarms["Pattern: two-sided CUSUM"], ewma=ew,
                   daily_alarm=alarms["Daily: proposed score OR band"])
    return summary, wf, pd.DataFrame([{"stock": code, **{k: v for k, v in thresholds.items()}, "cusum_k": CUSUM_K}])


# -------------------------------------------------------------- experiment D
def pattern_profile(code: str, wf: pd.DataFrame, start: str, end: str, label: str) -> dict:
    w = wf[in_window(wf["date"], start, end)]
    pre = wf[(wf["date"] < pd.Timestamp(start))].tail(ROBUST_WINDOW)
    if w.empty:
        return {"stock": code, "window": label, "trading_days": 0}
    scale_pre = 1.4826 * (pre["rel_resid"] - pre["rel_resid"].median()).abs().median()
    scale_in = 1.4826 * (w["rel_resid"] - w["rel_resid"].median()).abs().median()
    cum = float(np.expm1(np.log1p(w["rel_resid"]).sum()) * 100)
    neg_share = float((w["rel_resid"] < 0).mean())
    max_abs_z = float(w["rz"].abs().max())
    cusum_days = int(w["cusum_alarm"].sum())
    daily_days = int(w["daily_alarm"].sum())
    sustained = int(((w["cusum_minus"] > 0) | (w["cusum_plus"] > 0)).sum())
    abs_r = w["rel_resid"].abs()
    concentration = float(abs_r.max() / abs_r.sum()) if abs_r.sum() else 0.0
    open_share = sustained / len(w)
    # Descriptive criteria (not a trained classifier); several may apply.
    patterns = []
    if concentration >= 0.35:
        patterns.append("shock-dominated")
    if open_share >= 0.5 and abs(cum) >= 10:
        patterns.append("persistent drift " + ("down" if cum < 0 else "up"))
    if scale_pre and scale_in / scale_pre >= 2.0:
        patterns.append("volatility burst")
    if not patterns:
        patterns.append("none above criteria")
    return {"stock": code, "window": label, "start": start, "end": end, "trading_days": int(len(w)),
            "cumulative_residual_pct": cum, "negative_residual_share": neg_share,
            "residual_scale_ratio": float(scale_in / scale_pre) if scale_pre else float("nan"),
            "max_abs_robust_z": max_abs_z, "daily_alarm_days": daily_days, "cusum_alarm_days": cusum_days,
            "days_with_open_cusum": sustained, "open_cusum_share": open_share, "shock_concentration": concentration, "price_change_pct": float((w["actual_price"].iloc[-1] / w["prev_close"].iloc[0] - 1) * 100),
            "pattern": "; ".join(patterns)}


# -------------------------------------------------------------- experiment C
def diebold_mariano(e1: np.ndarray, e2: np.ndarray, power: int = 1, lags: int | None = None) -> tuple[float, float]:
    """DM test with Newey-West variance; H0 equal accuracy. Positive stat: model 1 worse."""
    from scipy import stats
    d = np.abs(e1) ** power - np.abs(e2) ** power
    n = len(d)
    lags = lags if lags is not None else int(math.floor(n ** (1 / 3)))
    dc = d - d.mean()
    gamma = [np.dot(dc[k:], dc[:n - k]) / n for k in range(lags + 1)]
    var = gamma[0] + 2 * sum((1 - k / (lags + 1)) * gamma[k] for k in range(1, lags + 1))
    stat = d.mean() / math.sqrt(var / n)
    # Exploratory HAC loss-difference statistic. No HLN correction is applied.
    # A single-origin multi-step path is not a sequence of one-day forecasts.
    p = 2 * (1 - stats.t.cdf(abs(stat), df=n - 1))
    return float(stat), float(p)


def experiment_c(code: str) -> list[dict]:
    lf = sorted((ROOT / "data" / "locked_forecasts").glob(f"{code}_forecast_created_*.csv"))[-1]
    act = sorted((ROOT / "data" / "actuals").glob(f"{code}_actual_through_*.csv"))[-1]
    f = pd.read_csv(lf, parse_dates=["date"])
    a = pd.read_csv(act, parse_dates=["date"])[["date", "close"]]
    m = f.merge(a, on="date", how="inner")
    out = []
    for path in ["ensemble_predicted_close", "scenario_lstm_close", "moving_average_drift_close"]:
        e_model = m[path] - m["close"]
        e_naive = m["naive_random_walk_close"] - m["close"]
        stat, p = diebold_mariano(e_model.to_numpy(), e_naive.to_numpy())
        out.append({"stock": code, "path": path, "matched_dates": int(len(m)), "mae_model": float(e_model.abs().mean()),
                    "mae_persistence": float(e_naive.abs().mean()), "dm_stat_abs_loss": stat, "p_value": p})
    return out


# -------------------------------------------------------------------- main
def eligibility(raw: pd.DataFrame) -> tuple[bool, str]:
    """Pre-specified inclusion rule for the multi-stock run (decided before results)."""
    d = raw["date"]
    if len(raw) < 1000:
        return False, f"only {len(raw)} sessions (<1000)"
    if d.min() > pd.Timestamp("2014-01-01"):
        return False, f"history starts {d.min().date()} (walk-forward needs ~2 years before 2016)"
    if d.max() < pd.Timestamp("2026-06-30"):
        return False, f"history ends {d.max().date()} (stale)"
    recent = raw[d >= d.max() - pd.Timedelta(days=365)]
    if (recent["volume"] > 0).mean() < 0.80:
        return False, "traded on <80% of sessions in the last year"
    return True, "eligible"


def run_stock(code: str, raw: pd.DataFrame, out_dir: Path, skip: set[str], reuse: bool) -> dict:
    from pattern_rules import null_rates, profile_window
    out_dir.mkdir(parents=True, exist_ok=True)
    status = {"stock": code, "rows": int(len(raw)), "first": str(raw["date"].min().date()),
              "last": str(raw["date"].max().date())}
    if "A" not in skip:
        t, meta = experiment_a(code, raw)
        t.to_csv(out_dir / "exp_a_detector_ablation.csv", index=False)
        pd.DataFrame([meta]).to_csv(out_dir / "exp_a_run_metadata.csv", index=False)
    if "B" not in skip:
        cache = out_dir / "walk_forward_residuals.csv"
        if reuse and cache.exists():
            wf = pd.read_csv(cache, parse_dates=["date"])
            wf["rz"] = robust_z(wf["rel_resid"])
            wf.attrs["blends"] = []
        else:
            wf = walk_forward_residuals(code, raw)
        s, wf2, thr = experiment_b(code, wf)
        s.to_csv(out_dir / "exp_b_episode_detection.csv", index=False)
        thr.to_csv(out_dir / "exp_b_thresholds.csv", index=False)
        if wf.attrs["blends"]:
            pd.DataFrame(wf.attrs["blends"]).to_csv(out_dir / "exp_b_walk_forward_fits.csv", index=False)
        wf2.to_csv(cache, index=False)
        cal_cache: dict[int, dict] = {}
        prof = [profile_window(code, wf2, e["start"], e["end"], f"{e['id']} {e['name']}", cal_cache) for e in EPISODES]
        prof.append(profile_window(code, wf2, CASE_WINDOW[0], CASE_WINDOW[1], "Case 2026 (unlabelled)", cal_cache))
        pd.DataFrame(prof).to_csv(out_dir / "exp_d_pattern_profiles.csv", index=False)
        pd.DataFrame(null_rates(code, wf2, EPISODES, *EVALUATION, cal_cache)).to_csv(out_dir / "exp_d_null_rates.csv", index=False)
    if "C" not in skip:
        try:
            pd.DataFrame(experiment_c(code)).to_csv(out_dir / "exp_c_diebold_mariano.csv", index=False)
        except IndexError:
            pass
    status["status"] = "done"
    return status


def main() -> None:
    from pattern_rules import RULES_SHA256, write_frozen_config
    parser = argparse.ArgumentParser()
    parser.add_argument("--stocks", nargs="+", default=["JKH", "BIL"],
                        help="codes, or ALL for every data/actuals/*_actual_through_*.csv")
    parser.add_argument("--csv", nargs="*", default=[], help="CODE=path overrides")
    parser.add_argument("--skip", nargs="*", default=[])
    parser.add_argument("--reuse", action="store_true", help="reuse cached walk-forward residuals")
    parser.add_argument("--resume", action="store_true", help="skip stocks that already have results")
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--data-dir", default=None, help="folder of <CODE>_actual_through_<date>.csv files")
    parser.add_argument("--shard", default="1/1", help="i/n: process every n-th stock starting at i (parallel runs)")
    args = parser.parse_args()
    global DATA_DIR
    if args.data_dir:
        DATA_DIR = (ROOT / args.data_dir) if not Path(args.data_dir).is_absolute() else Path(args.data_dir)
    override = dict(item.split("=", 1) for item in args.csv)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    write_frozen_config(out_root / "frozen_pattern_rules.json")

    stocks = args.stocks
    if stocks == ["ALL"]:
        stocks = sorted({p.name.split("_actual_through_")[0] for p in DATA_DIR.glob("*_actual_through_*.csv")})
    shard_i, shard_n = (int(x) for x in args.shard.split("/"))
    stocks = stocks[shard_i - 1::shard_n]
    log_path = out_root / (f"run_log_shard{shard_i}of{shard_n}.csv" if shard_n > 1 else "run_log.csv")
    log = pd.read_csv(log_path).to_dict("records") if log_path.exists() else []
    done = {r["stock"] for r in log if r.get("status") == "done"}
    for n, code in enumerate(stocks, 1):
        stock_dir = out_root / "per_stock" / code
        if args.resume and code in done:
            print(f"[{n}/{len(stocks)}] {code}: already done", flush=True)
            continue
        try:
            raw = load_history(code, override)
        except (IndexError, FileNotFoundError):
            log.append({"stock": code, "status": "excluded", "reason": "no history file"}); continue
        ok, reason = eligibility(raw)
        if not ok:
            print(f"[{n}/{len(stocks)}] {code}: excluded - {reason}", flush=True)
            log.append({"stock": code, "rows": len(raw), "status": "excluded", "reason": reason})
            continue
        print(f"[{n}/{len(stocks)}] {code}: rows={len(raw)} {raw['date'].min().date()}..{raw['date'].max().date()}", flush=True)
        try:
            log.append(run_stock(code, raw, stock_dir, set(args.skip), args.reuse))
        except Exception as exc:  # keep going; record why
            print(f"  {code} FAILED: {exc!r}", flush=True)
            log.append({"stock": code, "rows": len(raw), "status": "failed", "reason": repr(exc)[:300]})
        pd.DataFrame(log).drop_duplicates("stock", keep="last").to_csv(log_path, index=False)
    pd.DataFrame(log).drop_duplicates("stock", keep="last").to_csv(log_path, index=False)
    (out_root / "run_metadata.json").write_text(json.dumps({
        "seed": SEED, "episodes": EPISODES, "calibration_period": CALIBRATION, "evaluation_period": EVALUATION,
        "case_window": CASE_WINDOW, "alarm_budget": ALARM_BUDGET, "cusum_k": CUSUM_K, "robust_window": ROBUST_WINDOW,
        "bootstrap": {"reps": BOOT_REPS, "block": BOOT_BLOCK}, "pattern_rules_sha256": RULES_SHA256,
        "stocks_requested": stocks}, indent=2))
    print("saved", out_root, "- now run: python experiments/aggregate_results.py", flush=True)


if __name__ == "__main__":
    main()
