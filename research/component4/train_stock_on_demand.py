"""Fit one security's own risk classifier; never substitute another security.

The original research model remains untouched. Holdout metrics measure agreement
with the documented current-risk index, not prediction of investment losses.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import os
import uuid

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder

from train_cse_risk_model import (FEATURES, GLOBAL_FEATURES, FACTOR_SYMBOLS,
    FACTOR_HISTORY_PATH, _fetch_yahoo_series, prepare_dataset, chronological_split, metrics)

CACHE = Path(__file__).resolve().parents[2] / "server/uploads/factor-history"


def load_factors(history):
    start = pd.to_datetime(history["Date"]).min().to_pydatetime() - timedelta(days=45)
    end = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE / "global_daily_observed_v1.csv"
    for path in (cache_path, FACTOR_HISTORY_PATH):
        if path.exists():
            cached = pd.read_csv(path)
            dates = pd.to_datetime(cached["Date"])
            if dates.max() >= pd.Timestamp(end - timedelta(days=8)) and dates.min() <= pd.Timestamp(start + timedelta(days=45)):
                return cached
    merged = None
    for label, symbol in FACTOR_SYMBOLS.items():
        series = _fetch_yahoo_series(symbol, start, end, attempts=1, timeout=10).rename(columns={"Value": label})
        merged = series if merged is None else merged.merge(series, on="Date", how="outer")
    # Keep common observed sessions, not a synthetic calendar of filled prices.
    # prepare_dataset later joins only a preceding observation, at most 7 days old.
    combined = merged.sort_values("Date").dropna().reset_index(drop=True)
    temporary = cache_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    combined.to_csv(temporary, index=False)
    os.replace(temporary, cache_path)
    return combined


def fit_stock(history, symbol, factors=None):
    history = history.rename(columns={"date": "Date", "symbol": "Symbol", "close": "Close", "volume": "Volume"})
    if set(history["Symbol"].str.upper()) != {symbol}:
        raise ValueError("Risk training history must contain exactly the selected security.")
    if history["Date"].duplicated().any():
        raise ValueError("Duplicate risk-training dates require review.")
    factors = load_factors(history) if factors is None else factors
    dataset = prepare_dataset(history, factors, preserve_symbols=True, prior_global_close=True)
    train, test, details = chronological_split(dataset)
    if train["Risk_Label"].nunique() != 3:
        raise ValueError("This security does not provide enough varied evidence for three risk categories.")
    encoder = LabelEncoder().fit([symbol])
    train["Stock_encoded"] = 0
    test["Stock_encoded"] = 0
    settings = dict(n_estimators=180, max_depth=12, min_samples_leaf=3,
                    class_weight="balanced", random_state=42, n_jobs=1)
    model = RandomForestClassifier(**settings).fit(train[FEATURES], train["Risk_Label"])
    test_metrics = metrics(model, test, test["Risk_Label"], FEATURES)
    stock_features = [column for column in FEATURES if column not in GLOBAL_FEATURES]
    ablation = RandomForestClassifier(**settings).fit(train[stock_features], train["Risk_Label"])
    ablation_metrics = metrics(ablation, test, test["Risk_Label"], stock_features)
    majority = np.full(len(test), int(train["Risk_Label"].mode().iloc[0]))
    baseline = float(f1_score(test["Risk_Label"], majority, average="macro", zero_division=0))
    # Only after the chronological check, refit using all completed observations.
    # Risk cutoffs stay frozen to the training period; they are not retuned on test.
    all_rows = pd.concat([train, test])
    model.fit(all_rows[FEATURES], all_rows["Risk_Label"])
    metadata = {"model_version": "cse-security-specific-current-risk-rf-v1",
        "supported_stocks": [symbol], "fresh_fit": True, "created_at": datetime.now(timezone.utc).isoformat(),
        "history_sha256": hashlib.sha256(history.to_csv(index=False).encode()).hexdigest(),
        "factor_sha256": hashlib.sha256(factors.to_csv(index=False).encode()).hexdigest(),
        "factor_history_through": str(pd.to_datetime(factors["Date"]).max().date()),
        "features": FEATURES, "split_details": details, "test_metrics": test_metrics,
        "majority_baseline_macro_f1": baseline,
        "global_indicator_macro_f1_change": test_metrics["macro_f1"] - ablation_metrics["macro_f1"],
        "target_definition": "Stock-specific training-period tertiles of the existing transparent current-risk index.",
        "evaluation_scope": "Chronological 80/20 agreement with research-defined current-risk labels, not future-return or loss accuracy.",
        "factor_alignment": "Only a preceding calendar day's global close is eligible for a CSE historical session.",
        "refit_after_evaluation": True}
    return model, encoder, metadata
