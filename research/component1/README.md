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

## Anomaly evaluation in Jupyter

Open `notebooks/component1_anomaly_evaluation.ipynb` and choose **Run All** for
a quick demonstration of accuracy, precision, recall, F1, false alarms, missed
anomalies, method comparisons and confusion matrices for JKH and BIL. It checks
the saved summary metrics against row-level predictions. Dates and data sources
are shown explicitly: these are historical test results, not today's app output.

The same section is appended to both stock research notebooks (including their
root-level copies). After training in the same kernel it uses the current
`results`; when run independently it clearly labels the saved evidence instead.
The saved evaluation-cell outputs were executed independently; original training
outputs are preserved and training was not rerun for this addition.

The evaluation uses research **proxy labels**, not independent expert-confirmed
anomalies. An always-normal reference illustrates why accuracy alone is misleading
for rare anomalies. Forecast MAPE is not anomaly classification accuracy.

`build_anomaly_evaluation_notebook.py` regenerates these sections; passing
`--execute-sections` executes only the appended stock evaluation cells.

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

Before feature engineering, the pipeline checks dates, finite positive OHLC
prices, valid price ranges, and non-negative volume. Invalid observations are
excluded without filling or inventing prices; genuine price shocks and
zero-volume sessions remain. The live contract records received/used counts
and excluded dates under `data_quality`, and reports exclusions as warnings.
At least 300 valid observations are required. Duplicate dates must be resolved
explicitly rather than silently choosing a price. The quote importer also
rejects zero-price observations so they cannot poison subsequent analyses.

The 4-day, 1-month, 3-month, and 6-month values are checkpoints on a fresh
120-trading-session path. Favourable and adverse values are uncertainty bounds,
not guaranteed best/worst targets. The longer six-month checkpoint is presented
with the same baseline comparison and caution labels as the shorter horizons.

## Interpretation boundary

The validation evaluates forecast accuracy, not investment profitability. The
results are research evidence and are not buying or selling advice.

## Verified recent-history backfill

`server/src/services/marketHistoryService.js` runs before live training. It looks
for actual dated observations from CSE's public `companyChartDataByStock` feed
(period 5, approximately one year), starting after the latest uploaded history.
It does not assume every weekday was a trading day. Current-day observations are
excluded from historical backfill; the separate latest-quote refresh handles them.

CSE provides daily high, low, closing price and total share volume. Its public
chart commonly returns a null opening. For missing sessions only, the secondary
public TradingView CSELK candle supplies the opening when its date and daily
high/low match CSE. This cross-check corroborates the candle, not an independently
verified CSE opening. The source is explicitly recorded as
`cse-chart-history+tradingview-open`. A genuine opening already present in a CSE
snapshot can be retained instead. No opening is inferred from yesterday's close.

CSE remains authoritative for closing price and share volume: the secondary
feed can report a different last-traded price and exclude crossing volumes.
This repair does not retroactively reconcile all older CSV observations or
establish that their volume definitions agree with CSE's total volume. That
remaining source-consistency limitation matters for volume-scaled scores;
removing recent date gaps is not a claim that the entire dataset is independently
verified or that forecasting accuracy is guaranteed.
Adjusted closing prices are left null because a verified adjustment series is
not supplied. Valid uploaded rows are not silently overwritten. Invalid rows
and unfinished CSE snapshots can be repaired from the dated official history.

Before writes, private files in `server/uploads/history-backfills/` retain both
source responses, a SHA-256 fingerprint, the proposed changes and original rows.
This directory is ignored by Git. Insert-only upserts and version-checked updates
protect existing/concurrently changed records. Repeating the backfill is
idempotent. External source failure leaves honest warnings; it never produces
synthetic market observations. History older than the public trailing window
still needs an authorized full export.

```bash
cd server
# Preview only; no database writes.
npm run backfill:market-history -- --from 2026-08-29
# Apply after checking the preview; defaults to JKH.N0000 and BIL.N0000.
npm run backfill:market-history -- --from 2026-08-29 --apply
```

Install `websocket-client` from the pinned Component 1 requirements into the
environment selected by `PYTHON_BIN`. Opening-price fetching does not require
giving the application CSE or TradingView login credentials. If public access
becomes unavailable, unresolved dates remain flagged for a verified export.
The model, deviation formula, anomaly-score formula and threshold calibration
are unchanged by this ingestion repair. Analyze then fits against the repaired
MongoDB snapshot; saved results must be rerun to reflect the new history.

## Live training and progress

Every Analyze request refreshes the supported stocks from the public CSE trade
summary, checks the selected stock's recent daily history against the CSE chart,
backfills verified missing sessions, exports all stored history, validates it, and
fits models anew. It does not load the saved May predictions or reuse trained
weights. A unique run ID, training-completion time and input SHA-256 fingerprint
make this inspectable. Reproducible fits on unchanged observations may return
the same numbers, especially when the market is closed.

The expected-price/deviation stage still trains the chronological LSTM workflow
and calibrates anomaly thresholds. Live version 4 compares separate direct
log-return candidates for 4, 21, 60 and 120 observed sessions: Ridge with four
regularization settings, Random Forest, Extra Trees, gradient boosting, and an
explicit unchanged-price baseline. Inputs are
past price momentum, volatility, mean gaps, drawdown, volume and daily range.
An earlier frozen selection is evaluated on the chronological holdout. The live
winner is selected on a later, completed-outcome tuning period ending before the
live interval-calibration origins. Training targets precede tuning origins; tuning
targets precede calibration origins. Holdout/calibration prices never choose that
selection. A final refit on all completed targets produces the live estimate.
Empirical favourable/adverse ranges retain separate residual
calibration and a recent-volatility floor.

The live four-horizon workflow requires at least 1,000 valid observations so the
120-session targets have separate training, tuning, calibration and test periods.
The lower 300-row check belongs to the generic history-validation helper, not a
claim that 300 rows independently validate a six-month forecast.

The unchanged-price baseline is eligible to win and is labelled as such, not a
disguised learned forecast. Each horizon records all candidate tuning errors, the
selected candidate, selection boundaries, earlier held-out errors and caution
status. If the live winner differs from the earlier frozen winner, its earlier
holdout score is not presented as independent validation of that new live choice.
The best candidate in this bounded comparison is not a universally best model;
future accuracy and empirical interval coverage are not guaranteed.
The locked validation files remain unchanged.

A normal daily anomaly score cannot rule out a prolonged war/disaster impact.
The integrated explanation makes that distinction without changing the score or
threshold to force a desired anomaly. The history-based favourable/adverse bounds
are not calibrated event counterfactuals: the system does not know an exact price
if a war ends, and it must not claim one. Event-specific causal modelling and
prospective recovery validation remain separate research work.

Python emits `CSE_PROGRESS` events at actual stages and completed training epochs.
The backend logs them and relays owner-scoped events through
`GET /api/analysis/progress/:requestId`. The existing Analyze request remains
compatible; its optional UUID `clientRequestId` links the progress stream. The
bar represents workflow milestones, not an elapsed-time estimate. A failed run
never becomes a normal anomaly result. Progress lives in bounded server memory;
restarting the development process interrupts an in-flight analysis.

`GET /api/stocks/prices` lists every security returned by the public quote feed,
with the last reported trade date. Quote coverage does not imply trained-model
coverage: JKH and BIL retain their original validation scope, while additional
directory securities prepare genuine history and fit stock-specific models on
demand (see the root README). The quote endpoint is
a latest snapshot, not a complete historical backfill. The separate historical
backfill described below repairs recent gaps without inventing prices. Corporate
actions and exchange holidays still need
separate verification.

## Preserved model upgrade v2 evidence

The v2 comparison below documents the preceding model upgrade. Public fields and
other components' interfaces remain unchanged. Original May forecasts and
validation artifacts are preserved; new evidence is in `artifacts/upgrade_v2/`.

- The short-term expected-price model learns log price changes with relative
  price/volume features, Smooth L1 loss, gradient clipping and early stopping.
- Two learning rates and a learned-return/persistence blend are selected using
  validation data, never the test outcome. A zero blend is an explicit baseline
  fallback, not a claim that the neural network beat the baseline.
- The future path tests persistence, observed trends and damped trends separately
  at 4, 21, 60 and 120 sessions. It no longer forces recovery to a structural
  reference using weights evaluated only on one-day predictions.
- Selection, interval calibration and holdout origins have purged chronological
  boundaries: every earlier stage's target is known before the next stage starts.
- Live horizon selection uses completed historical outcomes. Empirical residual
  ranges include a recent-volatility floor; favourable/adverse paths are not
  guaranteed best/worst outcomes.
- Proxy-label tails and adaptive anomaly cutoffs use shifted past-only windows.
  Current and future scores cannot change the current cutoff. The original
  deviation/volume formula is unchanged; zero-volume scores are not treated as
  reliable liquidity confirmation. A separate prediction-band flag can still
  identify a price deviation when liquidity evidence is unavailable.

Run the reproducible comparison from the repository root:

```bash
python research/component1/evaluate_model_upgrade.py --epochs 18
python -m pytest research/component1/tests -q
```

The report distinguishes one-step holdouts, purged multi-session holdouts and
new retrospective hindcasts over the original May period. That May period
motivated the redesign, so improved hindcasts are not independent validation.
See `MODEL_UPGRADE_REPORT.md` for the formulas, measurements and remaining limits.
