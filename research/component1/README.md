# Component 1 Research Package

This folder preserves the market-modeling experiment and its out-of-sample
validation in a reproducible structure.

## Main validation notebook

Open and run:

`notebooks/component1_forecast_validation.ipynb`

The notebook compares the forecasts created on 10 May 2026 with market prices
that became available afterwards. It is written as a BSc-level research record:
each method, assumption, metric, limitation, and interpretation is explained
before the corresponding code.

## Reproduce the notebook

From this directory:

```bash
python build_validation_notebook.py
jupyter nbconvert --to notebook --execute \
  --inplace notebooks/component1_forecast_validation.ipynb
```

The executed notebook regenerates the CSV tables and PNG figures under
`artifacts/validation/`.

## Data lineage

- `data/training/` contains the historical snapshots available when the
  forecasts were made, ending on 7 May 2026.
- `data/locked_forecasts/` contains the forecasts created on 10 May 2026. These
  files are treated as immutable predictions during validation.
- `data/actuals/` contains later market observations downloaded through
  28 August 2026.
- `artifacts/validation/` contains exact-date matched observations, metrics,
  deviation diagnostics, and figures.

The old workspace contains timestamped forecasts for **JKH and BIL only**. A
third stock forecast was not found, so no third validation result is invented.

## Live application execution

`analyze_market_on_demand.py` is the application entry point. On every Analyze
request, the backend exports the selected stock's latest MongoDB rows to a
private temporary CSV, runs the pipeline again, returns a unique run ID and
data cut-off date, and deletes the temporary files. The locked May forecasts
above are never loaded as a live user result.

The 4-day, 1-month, 3-month, and 6-month values are checkpoints on a fresh
120-trading-session path. Favourable and adverse values are uncertainty bounds,
not guaranteed best/worst targets. The longer six-month checkpoint is presented
with the same baseline comparison and caution labels as the shorter horizons.

## Interpretation boundary

The validation evaluates forecast accuracy, not investment profitability. The
results are research evidence and are not buying or selling advice.
