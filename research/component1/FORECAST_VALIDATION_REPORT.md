# Three-Month Forecast Validation Report

## Research question

How accurately did the three-month forecasts locked in May 2026 predict the
subsequent closing prices of John Keells Holdings PLC (JKH) and Browns
Investments PLC (BIL)?

## Experimental design

The original historical datasets end on 7 May 2026. Forecast files created on
10 May 2026 contain 60 business-day predictions from 8 May to 30 July 2026.
Later price histories were collected independently and matched to each forecast
by exact calendar date. No forecast value was changed after observing the
actual prices.

There are 57 matched trading dates for each stock. Three forecast weekdays did
not have a corresponding CSE observation: 28 May, 29 June, and 29 July 2026.
These dates were excluded rather than filled with estimated values.

The historical sections of the later downloads were reconciled against every
row used by the original experiment. All 3,308 JKH rows and all 3,238 BIL rows
matched on date, OHLC prices, and volume. The 57-row validation windows contain
no duplicate dates, missing OHLCV values, invalid OHLC relationships, or
negative volumes.

## Results

| Stock | Model | MAE (LKR) | RMSE (LKR) | MAPE | Mean bias (forecast - actual) |
|---|---|---:|---:|---:|---:|
| JKH | Ensemble forecast | 1.416 | 1.594 | 7.07% | +1.416 |
| JKH | LSTM scenario | 1.109 | 1.260 | 5.54% | +1.107 |
| JKH | No-change baseline | **0.547** | **0.617** | **2.74%** | +0.544 |
| BIL | Ensemble forecast | 0.882 | 0.988 | 15.83% | +0.879 |
| BIL | LSTM scenario | 0.857 | 0.963 | 15.38% | +0.853 |
| BIL | No-change baseline | **0.656** | **0.728** | **11.76%** | +0.653 |

For JKH, the actual price was LKR 19.80 on 30 July, while the ensemble forecast
was LKR 22.53. The endpoint was overestimated by LKR 2.73, or 13.78% relative
to the actual price. The actual price declined by 3.88% between the first and
last matched dates while the scenario expected an upward path.

For BIL, the actual price was LKR 5.20 on 30 July, while the ensemble forecast
was LKR 6.87. The endpoint was overestimated by LKR 1.67, or 32.13%. The actual
price declined by 20.00% between the first and last matched dates while the
scenario expected an upward path.

The 80% prediction interval covered only 38.60% of JKH observations. The JKH
95% interval covered every observation, but its average width was LKR 8.91.
Both BIL intervals covered every observation, with average widths of LKR 2.57
and LKR 5.61. High coverage therefore does not imply accurate point forecasts;
the wide intervals make it easier to contain the realized prices.

## Interpretation

The locked three-month upward scenarios were **not validated** by the realized
market prices. Both forecasts had a positive bias, and the simple no-change
baseline achieved lower error for both stocks. This means the ensemble did not
add predictive value over a conservative baseline in this out-of-sample period.

This is still a useful research result. It demonstrates why forecasts must be
benchmarked and recalibrated rather than judged only by visual plausibility.
The next model iteration should consider shorter-horizon retraining, drift
monitoring, stronger baseline gating, and calibration of intervals separately
for each stock and horizon.

## Deviation and anomaly interpretation

The validation notebook also measures the daily difference between expected and
actual prices and standardizes the absolute difference into a diagnostic score.
This answers whether the realized path became unusually far from the locked
scenario. It is explicitly labelled a **post-forecast deviation diagnostic**.
It must not be confused with the original one-step liquidity-aware anomaly
detector, which uses contemporaneous prediction error and volume.

## Limitations

- Only two timestamped forecast files were found. A third stock cannot be
  validated without its original locked predictions and creation timestamp.
- The analysis covers one three-month market regime and cannot establish
  general model performance.
- Exact-date matching avoids fabricated prices but reduces the expected 60
  forecast weekdays to 57 observed CSE sessions.
- Percentage errors can appear large for lower-priced shares such as BIL.
- No trading costs, dividends, corporate actions, or investment strategy are
  evaluated.

## Reproducibility

The fully executed notebook is
`notebooks/component1_forecast_validation.ipynb`. Machine-readable results and
figures are stored in `artifacts/validation/`. The notebook records the formulas,
data-quality checks, date reconciliation, charts, and all values reported above.

