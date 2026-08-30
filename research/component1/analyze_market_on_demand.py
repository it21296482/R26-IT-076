"""Run a fresh market analysis from history supplied by the application.

The application writes the selected stock's current MongoDB history to a
temporary CSV. This entry point runs the research pipeline against that exact
snapshot and returns only the compact application contract.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from build_runtime_market_artifacts import build_contract
from src.component1_research import ResearchConfig, run_research_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fresh market analysis for one supported stock.")
    parser.add_argument("--input-csv", required=True, type=Path)
    parser.add_argument("--stock", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stock = args.stock.upper().split(".")[0]
    input_path = args.input_csv.resolve()
    output_path = args.output.resolve()
    history = pd.read_csv(input_path)
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError(f"Historical input is missing: {', '.join(sorted(missing))}")
    if len(history) < 300:
        raise ValueError("At least 300 historical trading sessions are required.")

    started_at = datetime.now(UTC)
    with tempfile.TemporaryDirectory(prefix=f"fresh-market-{stock.lower()}-") as temp_dir:
        expected_input = Path(temp_dir) / f"{stock}_ideabeam_historical.csv"
        shutil.copyfile(input_path, expected_input)
        results = run_research_pipeline(
            ResearchConfig(
                stock_code=stock,
                data_dir=temp_dir,
                artifact_dir=str(Path(temp_dir) / "artifacts"),
                epochs=max(1, args.epochs),
                forecast_horizon_days=120,
                verbose=False,
            )
        )

    contract = build_contract(stock, results, input_path)
    contract.update({
        "run_mode": "fresh_on_demand",
        "run_id": str(uuid.uuid4()),
        "analysis_started_at": started_at.isoformat(),
        "historical_row_count": int(len(history)),
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
