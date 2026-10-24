"""Explanation fidelity and circularity check (Experiment E).

For each stock: fit the 300-tree random-forest surrogate on train+validation
rows, report held-out test R^2 / Spearman (fidelity), Tree SHAP magnitude
shares and rolling top-3 ESI. Repeat with a volume-free target (band
severity) to test whether volume dominance is created by the score's own
volume denominator.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import component1_research as cr  # noqa: E402
from paper_experiments import OUT, SEED, load_history, residual_frame  # noqa: E402

FEATURES = cr.EXPLAIN_FEATURE_COLUMNS


def esi(values: pd.DataFrame, window=60, step=20, k=3) -> list[float]:
    tops = []
    for s in range(0, max(1, len(values) - window + 1), step):
        w = values.iloc[s:s + window]
        tops.append(set(w.abs().mean().sort_values(ascending=False).head(k).index))
    return [len(a & b) / k for a, b in zip(tops[1:], tops[:-1])]


def run(code: str) -> list[dict]:
    config = replace(cr.ResearchConfig(), stock_code=code, random_seed=SEED)
    cr.set_random_seed(SEED)
    eng = cr.engineer_features(load_history(code, {}))
    model_df = cr.prepare_model_frame(eng, feature_columns=cr.DEFAULT_FEATURE_COLUMNS)
    X, y, rows = cr.create_sequences(model_df, feature_columns=cr.DEFAULT_FEATURE_COLUMNS, lookback=config.lookback)
    tr, va = cr.split_indices(len(X), config.test_fraction, config.val_fraction)
    model, fs, ts, _ = cr.train_selected_price_model(X[:tr], y[:tr], X[tr:va], y[tr:va], config)
    pred = cr.predict_lstm(model, X, fs, ts)
    frame = residual_frame(rows.reset_index(drop=True), pred, y, config)
    bands = cr.calibrate_prediction_bands(frame.iloc[:tr], frame.iloc[tr:va], config)
    frame = residual_frame(rows.reset_index(drop=True), pred, y, config, bands)
    frame = frame.replace([np.inf, -np.inf], np.nan)
    out = []
    targets = {"volume-scaled score (log1p)": np.log1p(frame["liquidity_aware_anomaly_score"].clip(upper=1e6)),
               "band severity (volume-free)": frame["prediction_band_severity"]}
    for label, target in targets.items():
        data = pd.concat([frame[FEATURES], target.rename("target")], axis=1).dropna()
        fit = data.index < va
        test = data.index >= va
        rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=SEED, n_jobs=-1)
        rf.fit(data.loc[fit, FEATURES], data.loc[fit, "target"])
        p = rf.predict(data.loc[test, FEATURES])
        sv = shap.TreeExplainer(rf).shap_values(data.loc[test, FEATURES])
        sv = pd.DataFrame(sv, columns=FEATURES, index=data.index[test])
        share = (sv.abs().mean() / sv.abs().mean().sum()).sort_values(ascending=False)
        overlaps = esi(sv)
        out.append({"stock": code, "target": label, "test_rows": int(test.sum()),
                    "test_r2": float(r2_score(data.loc[test, "target"], p)),
                    "test_spearman": float(spearmanr(data.loc[test, "target"], p).correlation),
                    "top1": share.index[0], "top1_share_pct": float(share.iloc[0] * 100),
                    "top2": share.index[1], "top2_share_pct": float(share.iloc[1] * 100),
                    "top3": share.index[2], "top3_share_pct": float(share.iloc[2] * 100),
                    "esi_mean": float(np.mean(overlaps)) if overlaps else float("nan"),
                    "esi_windows": len(overlaps) + 1})
        print(out[-1], flush=True)
    return out


if __name__ == "__main__":
    rows = []
    for c in sys.argv[1:] or ["JKH", "BIL"]:
        rows += run(c)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "exp_e_explanations.csv", index=False)
