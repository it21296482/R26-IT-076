"""Train and evaluate the CSE-specific explainable market-risk classifier."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.preprocessing import LabelEncoder


ROOT = Path(__file__).resolve().parent
STOCK_HISTORY_PATH = ROOT / "data" / "cse_stock_history.csv"
FACTOR_HISTORY_PATH = ROOT / "data" / "cse_global_factors.csv"
MODEL_PATH = ROOT / "models" / "cse_risk_model.pkl"
ENCODER_PATH = ROOT / "models" / "cse_stock_encoder.pkl"
METADATA_PATH = ROOT / "models" / "cse_risk_model_metadata.json"
FEATURES = [
    "Close", "Volume", "MA10", "MA50", "Volatility", "Return20Pct",
    "Drawdown20Pct", "VolatilityPct", "VolumeRatio20", "Gold", "Oil", "VIX",
    "GoldChange30dPct", "OilChange30dPct", "VIXChange30dPct", "Stock_encoded",
]
GLOBAL_FEATURES = ["Gold", "Oil", "VIX", "GoldChange30dPct", "OilChange30dPct", "VIXChange30dPct"]
RISK_LABELS = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
FACTOR_SYMBOLS = {"Gold": "GC=F", "Oil": "CL=F", "VIX": "^VIX"}


def _fetch_yahoo_series(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    encoded = requests.utils.quote(symbol, safe="")
    params = {
        "period1": int(start.timestamp()),
        "period2": int(end.timestamp()),
        "interval": "1d",
        "events": "history",
    }
    last_error: Exception | None = None
    for host in ("query2.finance.yahoo.com", "query1.finance.yahoo.com"):
        for attempt in range(3):
            try:
                response = requests.get(
                    f"https://{host}/v8/finance/chart/{encoded}",
                    params=params,
                    headers={"User-Agent": "CSE-Insight-Research/1.0"},
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()["chart"]["result"][0]
                frame = pd.DataFrame({
                    "Date": pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_localize(None).normalize(),
                    "Value": result["indicators"]["quote"][0]["close"],
                }).dropna()
                if len(frame) < 100:
                    raise ValueError(f"Only {len(frame)} observations were returned for {symbol}.")
                return frame.drop_duplicates("Date", keep="last").sort_values("Date")
            except (KeyError, TypeError, ValueError, requests.RequestException) as error:
                last_error = error
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not refresh {symbol}: {last_error}")


def refresh_factor_history(stock_history: pd.DataFrame) -> pd.DataFrame:
    start = pd.to_datetime(stock_history["Date"]).min().to_pydatetime() - timedelta(days=7)
    end = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2)
    merged: pd.DataFrame | None = None
    for label, symbol in FACTOR_SYMBOLS.items():
        series = _fetch_yahoo_series(symbol, start, end).rename(columns={"Value": label})
        merged = series if merged is None else merged.merge(series, on="Date", how="outer")
    assert merged is not None
    merged = merged.sort_values("Date").ffill().dropna()
    FACTOR_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(FACTOR_HISTORY_PATH, index=False)
    return merged


def current_risk_score(frame: pd.DataFrame) -> pd.Series:
    """Build a transparent current-risk index before classifying it with RF."""
    return (
        0.35 * np.clip(frame["VolatilityPct"] / 8, 0, 1)
        + 0.25 * np.clip((-frame["Return20Pct"]).clip(lower=0) / 20, 0, 1)
        + 0.15 * np.clip((-frame["Drawdown20Pct"]).clip(lower=0) / 15, 0, 1)
        + 0.10 * np.clip((frame["VIX"] - 12) / 28, 0, 1)
        + 0.05 * np.clip(frame["OilChange30dPct"].abs() / 20, 0, 1)
        + 0.05 * np.clip(frame["GoldChange30dPct"].abs() / 15, 0, 1)
        + 0.05 * np.clip((frame["VolumeRatio20"] - 1).clip(lower=0) / 4, 0, 1)
    )


def prepare_dataset(stock_history: pd.DataFrame, factor_history: pd.DataFrame) -> pd.DataFrame:
    stocks = stock_history.copy()
    stocks["Date"] = pd.to_datetime(stocks["Date"]).dt.normalize()
    stocks["Stock"] = stocks["Symbol"].str.upper().str.split(".").str[0]
    stocks = stocks.sort_values(["Stock", "Date"]).drop_duplicates(["Stock", "Date"], keep="last")

    factors = factor_history.copy()
    factors["Date"] = pd.to_datetime(factors["Date"]).dt.normalize()
    factors = factors.sort_values("Date").drop_duplicates("Date", keep="last")
    for factor in FACTOR_SYMBOLS:
        factors[f"{factor}Change30dPct"] = factors[factor].pct_change(21) * 100

    prepared = []
    for stock, group in stocks.groupby("Stock", sort=True):
        group = group.sort_values("Date").copy()
        group["MA10"] = group["Close"].shift(1).rolling(10).mean()
        group["MA50"] = group["Close"].shift(1).rolling(50).mean()
        group["Volatility"] = group["Close"].shift(1).rolling(10).std(ddof=1)
        group["Return20Pct"] = group["Close"].pct_change(20) * 100
        group["Drawdown20Pct"] = ((group["Close"] / group["Close"].rolling(20).max()) - 1) * 100
        group["VolatilityPct"] = (group["Volatility"] / group["MA10"]) * 100
        prior_volume_median = group["Volume"].shift(1).rolling(20).median().replace(0, np.nan)
        group["VolumeRatio20"] = group["Volume"] / prior_volume_median
        group = pd.merge_asof(
            group.sort_values("Date"),
            factors,
            on="Date",
            direction="backward",
            tolerance=pd.Timedelta(days=7),
        )
        group["Stock"] = stock
        group["Risk_Score"] = current_risk_score(group)
        prepared.append(group)
    result = pd.concat(prepared, ignore_index=True)
    numeric = [feature for feature in FEATURES if feature != "Stock_encoded"] + ["Risk_Score"]
    result[numeric] = result[numeric].apply(pd.to_numeric, errors="coerce")
    return result.dropna(subset=numeric).reset_index(drop=True)


def chronological_split(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    train_parts = []
    test_parts = []
    details: dict[str, Any] = {}
    for stock, group in dataset.groupby("Stock", sort=True):
        group = group.sort_values("Date").reset_index(drop=True)
        split_index = int(len(group) * 0.8)
        if split_index < 100 or len(group) - split_index < 50:
            raise ValueError(f"Not enough chronological observations to train and test {stock}.")
        train = group.iloc[:split_index].copy()
        test = group.iloc[split_index:].copy()
        low, high = train["Risk_Score"].quantile([1 / 3, 2 / 3]).tolist()
        classify = lambda score: 0 if score <= low else 1 if score <= high else 2
        train["Risk_Label"] = train["Risk_Score"].map(classify)
        test["Risk_Label"] = test["Risk_Score"].map(classify)
        train_parts.append(train)
        test_parts.append(test)
        details[stock] = {
            "train_rows": len(train),
            "test_rows": len(test),
            "train_start": train["Date"].min().date().isoformat(),
            "train_end": train["Date"].max().date().isoformat(),
            "test_start": test["Date"].min().date().isoformat(),
            "test_end": test["Date"].max().date().isoformat(),
            "low_medium_threshold": round(float(low), 8),
            "medium_high_threshold": round(float(high), 8),
        }
    return pd.concat(train_parts), pd.concat(test_parts), details


def metrics(model: RandomForestClassifier, frame: pd.DataFrame, labels: pd.Series, features: list[str]) -> dict[str, Any]:
    prediction = model.predict(frame[features])
    return {
        "accuracy": round(float(accuracy_score(labels, prediction)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(labels, prediction)), 6),
        "macro_f1": round(float(f1_score(labels, prediction, average="macro")), 6),
        "confusion_matrix": confusion_matrix(labels, prediction, labels=[0, 1, 2]).tolist(),
        "class_report": classification_report(
            labels,
            prediction,
            labels=[0, 1, 2],
            target_names=[RISK_LABELS[index] for index in range(3)],
            output_dict=True,
            zero_division=0,
        ),
    }


def train(refresh_factors: bool = False) -> dict[str, Any]:
    history = pd.read_csv(STOCK_HISTORY_PATH)
    factor_history = (
        refresh_factor_history(history)
        if refresh_factors or not FACTOR_HISTORY_PATH.exists()
        else pd.read_csv(FACTOR_HISTORY_PATH)
    )
    dataset = prepare_dataset(history, factor_history)
    train_rows, test_rows, split_details = chronological_split(dataset)

    encoder = LabelEncoder().fit(sorted(dataset["Stock"].unique()))
    for frame in (train_rows, test_rows):
        frame["Stock_encoded"] = encoder.transform(frame["Stock"])

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    ).fit(train_rows[FEATURES], train_rows["Risk_Label"])

    stock_only_features = [feature for feature in FEATURES if feature not in GLOBAL_FEATURES]
    ablation = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    ).fit(train_rows[stock_only_features], train_rows["Risk_Label"])

    test_metrics = metrics(model, test_rows, test_rows["Risk_Label"], FEATURES)
    ablation_metrics = metrics(ablation, test_rows, test_rows["Risk_Label"], stock_only_features)
    majority = int(train_rows["Risk_Label"].mode().iloc[0])
    baseline = np.full(len(test_rows), majority)
    baseline_macro_f1 = float(f1_score(test_rows["Risk_Label"], baseline, average="macro", zero_division=0))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH, compress=3)
    joblib.dump(encoder, ENCODER_PATH, compress=3)
    metadata = {
        "model_version": "cse-current-risk-rf-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "supported_stocks": encoder.classes_.tolist(),
        "features": FEATURES,
        "target_definition": (
            "LOW/MEDIUM/HIGH tertiles within each stock's chronological training period. "
            "The transparent current-risk index combines recent price variability, 20-session return and drawdown, "
            "unusual volume, VIX level, and 30-day Gold and Oil movement."
        ),
        "classification_scope": "Current observable financial-market risk state; not a future-loss forecast.",
        "split_method": "Chronological 80/20 split within each stock.",
        "split_details": split_details,
        "training_class_counts": {
            RISK_LABELS[int(label)]: int(count)
            for label, count in train_rows["Risk_Label"].value_counts().sort_index().items()
        },
        "test_class_counts": {
            RISK_LABELS[int(label)]: int(count)
            for label, count in test_rows["Risk_Label"].value_counts().sort_index().items()
        },
        "test_metrics": test_metrics,
        "majority_baseline_macro_f1": round(baseline_macro_f1, 6),
        "stock_only_ablation_macro_f1": ablation_metrics["macro_f1"],
        "global_indicator_macro_f1_change": round(test_metrics["macro_f1"] - ablation_metrics["macro_f1"], 6),
        "feature_importance": {
            feature: round(float(importance), 8)
            for feature, importance in sorted(
                zip(FEATURES, model.feature_importances_),
                key=lambda item: item[1],
                reverse=True,
            )
        },
        "limitations": [
            "The model is evaluated only on BIL and JKH and must not be used for an unseen stock.",
            "Risk labels are research-derived current market-risk categories, not future-loss predictions or advice.",
            "Test metrics measure fidelity to the documented risk-index labels, not investment-return forecasting accuracy.",
            "SHAP explains model contribution and does not establish real-world causation.",
        ],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the BIL/JKH explainable risk model.")
    parser.add_argument("--refresh-factors", action="store_true")
    args = parser.parse_args()
    print(json.dumps(train(refresh_factors=args.refresh_factors), indent=2))


if __name__ == "__main__":
    main()
