"""Reproduce the v2 comparison without altering any locked forecast or old result."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
import tempfile

import pandas as pd
import torch

from src.component1_research import ResearchConfig, run_research_pipeline
from src.horizon_forecast import calibrated_horizon_forecast
from build_runtime_market_artifacts import build_contract

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=18)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "upgrade_v2")
    args = parser.parse_args()
    torch.set_num_threads(1)
    args.output.mkdir(parents=True, exist_ok=True)
    comparisons, horizon_rows, replay_rows = [], [], []
    for stock in ("JKH", "BIL"):
        source = ROOT / "data" / "actuals" / f"{stock}_actual_through_2026-08-28.csv"
        for mode in ("legacy_price", "log_return"):
            print(f"Training {stock}: {mode}", flush=True)
            with tempfile.TemporaryDirectory() as temporary:
                shutil.copyfile(source, Path(temporary) / f"{stock}_ideabeam_historical.csv")
                results = run_research_pipeline(ResearchConfig(
                    stock_code=stock, data_dir=temporary, epochs=args.epochs,
                    price_model_mode=mode, forecast_horizon_days=120,
                    adaptive_anomaly_window=0 if mode == "legacy_price" else 252,
                ))
            comparisons.append({
                "stock": stock, "mode": mode, "epochs_requested": args.epochs,
                "epochs_completed": len(results["training_history"]["val_loss"]),
                "data_cutoff": str(results["raw_data"].date.max().date()),
                "test_observations": len(results["test_results"]),
                "test_mae_lkr": results["prediction_metrics"]["mae"],
                "test_rmse_lkr": results["prediction_metrics"]["rmse"],
                "test_mape_pct": results["prediction_metrics"]["mape_pct"],
                "baseline_mae_lkr": results["naive_baseline_metrics"]["mae"],
                "return_blend": results["dashboard_output"]["model_upgrade"]["validation_return_blend"],
            })
            if mode != "log_return":
                continue
            contract = build_contract(stock, results, source)
            (args.output / f"{stock.lower()}_market_insight.json").write_text(json.dumps(contract, indent=2), encoding="utf-8")
            calibration = results["forecast_3m"].attrs["calibration"]
            for horizon, fit in calibration["horizons"].items():
                test = fit["holdout"]
                if test["status"] == "retrospective_purged_holdout":
                    horizon_rows.append({"stock": stock, "sessions": int(horizon),
                        "live_candidate": fit["live_candidate"], "holdout_candidate": test["selected_candidate"],
                        "observations": test["observations"], "mae_lkr": test["selected"]["mae_lkr"],
                        "baseline_mae_lkr": test["baseline"]["mae_lkr"],
                        "interval_95_coverage": test["interval_95_coverage"],
                        "beats_baseline": test["beats_baseline_mae"]})

        # Newly designed hindcast: only the original May snapshot enters this calculation.
        # This period motivated the upgrade, so it is not independent confirmation.
        training = pd.read_csv(ROOT / "data" / "training" / f"{stock}_history_through_2026-05-07.csv", parse_dates=["date"])
        path = calibrated_horizon_forecast(training, 60)
        original_matched = pd.read_csv(ROOT / "artifacts" / "validation" / f"{stock}_forecast_vs_actual.csv", parse_dates=["date"])
        matched = original_matched[["date", "close", "ensemble_predicted_close"]].merge(
            path[["date", "predicted_close"]], on="date", how="inner")
        matched["old_absolute_error"] = (matched.close - matched.ensemble_predicted_close).abs()
        matched["new_absolute_error"] = (matched.close - matched.predicted_close).abs()
        matched.to_csv(args.output / f"{stock.lower()}_may_hindcast_comparison.csv", index=False)
        replay_rows.append({"stock": stock, "matched_sessions": len(matched),
            "locked_ensemble_mae_lkr": float(matched.old_absolute_error.mean()),
            "new_hindcast_mae_lkr": float(matched.new_absolute_error.mean()),
            "status": "retrospective_hindcast_on_development_period_not_independent_test"})

    pd.DataFrame(comparisons).to_csv(args.output / "one_step_comparison.csv", index=False)
    pd.DataFrame(horizon_rows).to_csv(args.output / "horizon_holdout_comparison.csv", index=False)
    pd.DataFrame(replay_rows).to_csv(args.output / "may_hindcast_summary.csv", index=False)
    (args.output / "run_metadata.json").write_text(json.dumps({
        "generated_at": datetime.now(UTC).isoformat(), "seed": 42,
        "python_torch_version": torch.__version__, "epochs_requested": args.epochs,
        "scope": "JKH and BIL saved historical snapshots; no fresh exchange download",
        "limitations": "Retrospective development evaluation; require new prospective forecasts for independent confirmation. Overlapping origins are not independent samples.",
    }, indent=2), encoding="utf-8")
    print(pd.DataFrame(comparisons).to_string(index=False), flush=True)
    print(pd.DataFrame(replay_rows).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
