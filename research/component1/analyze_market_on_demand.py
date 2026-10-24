"""Run a fresh market analysis from history supplied by the application.

The application writes the selected stock's current MongoDB history to a
temporary CSV. This entry point runs the research pipeline against that exact
snapshot and returns only the compact application contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import torch

from build_runtime_market_artifacts import build_contract
from src.component1_research import ResearchConfig, run_research_pipeline, validate_market_history, normalize_stock_code
from src.runtime_progress import report_progress


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fresh market analysis for one supported stock.")
    parser.add_argument("--input-csv", required=True, type=Path)
    parser.add_argument("--stock", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_progress("loading_history", 1)
    torch.set_num_threads(1)
    stock = normalize_stock_code(args.stock)
    if not re.fullmatch(r"[A-Z0-9]+(?:\.[NX][0-9]{4})?", stock):
        raise ValueError("Invalid CSE stock identifier.")
    input_path = args.input_csv.resolve()
    output_path = args.output.resolve()
    history = pd.read_csv(input_path)
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError(f"Historical input is missing: {', '.join(sorted(missing))}")
    if len(validate_market_history(history)) < 1000:
        raise ValueError("At least 1000 valid historical observations are required to train and independently check all four horizons.")

    started_at = datetime.now(UTC)
    # Each Analyze request starts a fresh pipeline on its supplied CSV snapshot.
    # The temporary workspace is deleted on exit. Models live in memory; this
    # entry point exports compact results, not reusable trained-weight checkpoints.
    with tempfile.TemporaryDirectory(prefix=f"fresh-market-{stock.lower()}-") as temp_dir:
        expected_input = Path(temp_dir) / f"{stock}_ideabeam_historical.csv"
        shutil.copyfile(input_path, expected_input)
        results = run_research_pipeline(
            ResearchConfig(
                stock_code=stock,
                data_dir=temp_dir,
                artifact_dir=str(Path(temp_dir) / "artifacts"),
                epochs=max(1, args.epochs),
                forecast_horizon_days=120,  # Enables 4, 21, 60 and 120-session outputs.
                verbose=False,
            )
        )

    contract = build_contract(stock, results, input_path)
    report_progress("checking_output", 95)
    contract.update({
        "run_mode": "fresh_on_demand",
        "run_id": str(uuid.uuid4()),
        "analysis_started_at": started_at.isoformat(),
        "historical_row_count": int(len(results["raw_data"])),
        "training": {
            # Provenance proves which input snapshot was used, not model accuracy.
            # Identical data/settings can correctly produce identical predictions.
            "fresh_fit": True,
            "data_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
            "completed_at": datetime.now(UTC).isoformat(),
            "forecast_method": "purged_per_horizon_model_selection",
            "reproducibility_note": "Fresh fits on unchanged observations can correctly reproduce the same estimates.",
        },
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    report_progress("market_complete", 100)


if __name__ == "__main__":
    main()
