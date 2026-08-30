"""Build versioned market-analysis artifacts used by the MERN application.

This script runs the Component 1 research pipeline against the latest available
history for each supported stock and exposes checkpoints through 120 trading
sessions. Longer-horizon estimates retain uncertainty and caution labels.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.component1_research import ResearchConfig, run_research_pipeline, save_research_artifacts


ROOT = Path(__file__).resolve().parent
DEFAULT_ACTUALS = ROOT / "data" / "actuals"
DEFAULT_OUTPUT = ROOT / "artifacts" / "runtime"
HORIZONS = (
    ("4d", 4, "4 trading days"),
    ("1m", 21, "1 month"),
    ("3m", 60, "3 months"),
    ("6m", 120, "6 months"),
)


def json_value(value: Any) -> Any:
    """Convert NumPy/Pandas scalar values into JSON-safe Python values."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def horizon_summary(
    forecast: pd.DataFrame,
    key: str,
    step: int,
    label: str,
    current_price: float,
    advanced_model_beats_naive: bool,
) -> dict[str, Any]:
    row = forecast.loc[forecast["forecast_step"] == step].iloc[0]
    estimate = float(row["ensemble_predicted_close"])
    change_pct = ((estimate / current_price) - 1.0) * 100.0
    if change_pct > 1.0:
        direction = "higher"
    elif change_pct < -1.0:
        direction = "lower"
    else:
        direction = "broadly stable"

    return {
        "key": key,
        "label": label,
        "sessions": step,
        "target_date": pd.Timestamp(row["date"]).date().isoformat(),
        "estimated_close_lkr": round(estimate, 4),
        "change_from_latest_pct": round(change_pct, 4),
        "direction": direction,
        "lower_80_lkr": round(float(row["lower_80"]), 4),
        "upper_80_lkr": round(float(row["upper_80"]), 4),
        "lower_95_lkr": round(float(row["lower_95"]), 4),
        "upper_95_lkr": round(float(row["upper_95"]), 4),
        "status": "available" if advanced_model_beats_naive else "available_with_caution",
    }


def deviation_history(test_results: pd.DataFrame, threshold: float) -> dict[str, Any]:
    """Summarize recent actual-versus-expected gaps for event-window comparison."""
    rows = test_results.sort_values("date").tail(90).copy()
    rows["deviation_pct"] = (
        (rows["actual_price"] - rows["predicted_price"])
        / rows["predicted_price"].replace(0, pd.NA)
        * 100
    )
    flagged = rows.loc[rows["final_anomaly_detected"].astype(bool)].copy()
    largest = rows.assign(abs_pct=rows["deviation_pct"].abs()).nlargest(5, "abs_pct")

    def record(row: pd.Series) -> dict[str, Any]:
        return {
            "date": pd.Timestamp(row["date"]).date().isoformat(),
            "actual_price_lkr": round(float(row["actual_price"]), 4),
            "expected_price_lkr": round(float(row["predicted_price"]), 4),
            "signed_deviation_lkr": round(float(row["actual_price"] - row["predicted_price"]), 4),
            "deviation_pct": round(float(row["deviation_pct"]), 4),
            "anomaly_score": round(float(row["liquidity_aware_anomaly_score"]), 6),
            "threshold": round(float(threshold), 6),
            "detected": bool(row["final_anomaly_detected"]),
            "side": str(row.get("anomaly_side", "none")),
            "risk_level": str(row.get("risk_level", "Unknown")),
        }

    return {
        "window_start": pd.Timestamp(rows["date"].min()).date().isoformat(),
        "window_end": pd.Timestamp(rows["date"].max()).date().isoformat(),
        "observations": int(len(rows)),
        "detected_count": int(len(flagged)),
        "detected_events": [record(row) for _, row in flagged.tail(10).iterrows()],
        "largest_recent_deviations": [record(row) for _, row in largest.sort_values("date").iterrows()],
        "interpretation": (
            "Dates can be compared with dated external events, but timing overlap alone does not prove causation."
        ),
    }


def build_contract(stock: str, results: dict[str, Any], source_file: Path) -> dict[str, Any]:
    dashboard = results["dashboard_output"]
    forecast = results["forecast_3m"].sort_values("forecast_step").reset_index(drop=True)
    latest = results["test_results"].sort_values("date").iloc[-1]
    current_price = float(dashboard["current_price"])
    advanced_model_beats_naive = bool(
        results["prediction_metrics"]["mae"] < results["naive_baseline_metrics"]["mae"]
    )
    anomaly_threshold = float(results["anomaly_threshold_selection"]["liquidity_threshold"])
    supported_horizons = [
        horizon_summary(forecast, key, step, label, current_price, advanced_model_beats_naive)
        for key, step, label in HORIZONS
    ]
    top_factors = []
    for item in dashboard.get("top_shap_factors", []):
        if isinstance(item, dict):
            top_factors.append({str(key): json_value(value) for key, value in item.items()})

    return {
        "schema_version": "1.0",
        "symbol": str(dashboard.get("stock") or f"{stock}.N0000"),
        "as_of_date": pd.Timestamp(results["raw_data"]["date"].max()).date().isoformat(),
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": source_file.name,
        "current_price_lkr": round(current_price, 4),
        "horizons": supported_horizons,
        "anomaly": {
            "detected": bool(latest.get("final_anomaly_detected", False)),
            "type": str(dashboard.get("anomaly_type", "Normal movement")),
            "actual_price_lkr": round(float(latest["actual_price"]), 4),
            "expected_price_lkr": round(float(latest["predicted_price"]), 4),
            "signed_deviation_lkr": round(float(latest["actual_price"] - latest["predicted_price"]), 4),
            "absolute_deviation_lkr": round(float(latest["deviation"]), 4),
            "liquidity_aware_score": round(float(latest["liquidity_aware_anomaly_score"]), 6),
            "threshold": round(anomaly_threshold, 6),
            "side": str(latest.get("anomaly_side", "none")),
            "risk_level": str(latest.get("risk_level", "Unknown")),
            "explanation": str(dashboard.get("simple_explanation", dashboard.get("shock_adjusted_explanation", ""))),
        },
        "deviation_history": deviation_history(results["test_results"], anomaly_threshold),
        "model_quality": {
            "forecast_reliability_score": json_value(dashboard.get("forecast_reliability_score")),
            "forecast_reliability_interpretation": dashboard.get("forecast_reliability_interpretation"),
            "test_mae_lkr": round(float(results["prediction_metrics"]["mae"]), 6),
            "test_mape_pct": round(float(results["prediction_metrics"]["mape_pct"]), 6),
            "naive_test_mae_lkr": round(float(results["naive_baseline_metrics"]["mae"]), 6),
            "advanced_model_beats_naive_mae": advanced_model_beats_naive,
            "comparative_assessment": (
                "advanced_model_outperformed_baseline"
                if advanced_model_beats_naive
                else "baseline_not_beaten_use_forecast_with_caution"
            ),
        },
        "top_factors": top_factors,
        "limitations": dashboard.get("limitations", []),
        "non_advisory_note": "This is a model-based research estimate for decision support, not buying or selling advice.",
    }


def build_one(stock: str, actuals_dir: Path, output_dir: Path, epochs: int) -> Path:
    source_file = actuals_dir / f"{stock}_actual_through_2026-08-28.csv"
    if not source_file.exists():
        raise FileNotFoundError(f"Latest history is unavailable for {stock}: {source_file}")

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_output_dir = output_dir / "raw" / stock.lower()
    with tempfile.TemporaryDirectory(prefix=f"component1-{stock.lower()}-") as temp_dir:
        expected_source = Path(temp_dir) / f"{stock}_ideabeam_historical.csv"
        shutil.copyfile(source_file, expected_source)
        config = ResearchConfig(
            stock_code=stock,
            data_dir=temp_dir,
            artifact_dir=str(raw_output_dir),
            epochs=epochs,
            forecast_horizon_days=120,
            verbose=False,
        )
        results = run_research_pipeline(config)
        save_research_artifacts(results, raw_output_dir)

    contract = build_contract(stock, results, source_file)
    contract_path = output_dir / f"{stock.lower()}_market_insight.json"
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    return contract_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build current Component 1 application artifacts.")
    parser.add_argument("--stocks", nargs="+", default=["JKH", "BIL"])
    parser.add_argument("--actuals-dir", type=Path, default=DEFAULT_ACTUALS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for stock in args.stocks:
        path = build_one(stock.upper(), args.actuals_dir.resolve(), args.output_dir.resolve(), args.epochs)
        print(path)


if __name__ == "__main__":
    main()
