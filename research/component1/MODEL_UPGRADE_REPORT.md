# Component 1: model upgrade and evidence

## Plain-English outcome

The old model sometimes predicted a rising path while actual prices fell. Its
long-range path also pulled prices towards a historical reference even when
there was no validated reason for recovery. The upgrade removes that forced
recovery. It checks which price pattern worked on earlier examples at the same
forecast horizon, and keeps the unchanged-price baseline when the alternatives
do not provide a clear validation improvement.

This is a safer and more accurate result than the old model in the comparisons
below. It is not a model that can predict every situation, and it has not proven
that it beats a simple unchanged-price forecast on these stocks.

## What was changed

1. The expected-price model now learns relative price changes instead of raw
   historical price levels. Prices and volumes are normalized within each
   lookback window. Training uses Smooth L1 loss, gradient clipping and early
   stopping to reduce sensitivity to extreme errors.
2. Learning rates 0.001 and 0.0003 are compared on validation MAE. The learned
   return is blended with persistence using validation-selected weights
   0, 0.1, 0.25, 0.5 or 1. A zero weight means the baseline won. Test outcomes
   do not select the rate or blend.
3. Future forecasts separately compare persistence, 20/60-session trends and
   damped trends at 4, 21, 60 and 120 sessions. The candidate must improve
   selection error over persistence by at least 5%; otherwise persistence wins.
   These horizon models are distinct from the one-session neural model used
   to calculate expected-price deviations.
4. Horizon selection, interval calibration and test periods are purged:
   an earlier origin's target must finish before the next period begins.
   Live selection can use completed past outcomes, but its own predictions
   are not passed off as independent test results.
5. Financial-anomaly proxy labels no longer use full-series tail quantiles.
   They use lagged 252-session windows with at least 60 past observations.
   Flat prices and continuously rising prices no longer disappear because
   an undefined RSI calculation dropped their rows.
6. The anomaly cutoff adapts from earlier observations only. Zero-volume
   scores are preserved for calculation transparency but cannot by themselves
   trigger a liquidity anomaly. The independent price-band check remains.
7. Multi-session ranges use horizon-specific residuals, with a recent-volatility
   floor and nested, nondecreasing widths. This can widen the range after a
   shock, but does not identify the cause of a shock or promise coverage.
8. Application contracts include the learning-rate comparison, selected blend,
   per-horizon tests, calibration counts and threshold policy. Historical
   deviation records carry the cutoff that actually applied on each date.

## Measured comparison

Source snapshots end on **28 August 2026**, not today's live exchange price.
Seed 42; maximum 18 epochs; chronological train/validation/test splits;
663 JKH and 649 BIL one-session test observations. Both modes use the same
updated data preparation. Therefore the old-mode rows are a controlled
price-level-model ablation, not a bit-for-bit rerun of all historic code.

| Stock | Old price-level MAE (Rs.) | Upgraded MAE (Rs.) | Unchanged-price MAE (Rs.) | Upgraded MAPE |
| --- | ---: | ---: | ---: | ---: |
| JKH | 0.366163 | 0.191758 | 0.191407 | 0.9263% |
| BIL | 0.136047 | 0.103082 | 0.103082 | 1.6123% |

MAE improved by approximately 47.6% for JKH and 24.2% for BIL relative to
the price-level model. **Neither result demonstrates a meaningful win over
persistence.** BIL selected a zero learned-return blend. Tiny floating-point
differences are not counted as an advanced-model improvement.

Both stocks selected learning rate 0.001. JKH selected return weight 0.25;
BIL selected 0. No test result was used to override those choices.

### Original three-month period

The new horizon forecaster was replayed using only the snapshot ending
7 May 2026 and matched to the same 57 later observations per stock.

| Stock | Original locked ensemble MAE (Rs.) | New retrospective hindcast MAE (Rs.) |
| --- | ---: | ---: |
| JKH | 1.415742 | 0.547368 |
| BIL | 0.882175 | 0.656140 |

The new path selected persistence. The original period motivated this redesign,
so these are **development-period hindcasts**, not a newly achieved prospective
forecast. The original saved forecasts and validation files were not overwritten.

### Separate multi-session checks

Purged retrospective holdouts selected persistence at every tested horizon.
The v2 live refit also selected persistence for these two snapshots.

| Stock | Sessions | Holdout origins | Selected-model MAE (Rs.) |
| --- | ---: | ---: | ---: |
| JKH | 4 | 134 | 0.431605 |
| JKH | 21 | 131 | 1.146975 |
| JKH | 60 | 123 | 1.901133 |
| JKH | 120 | 111 | 1.680448 |
| BIL | 4 | 131 | 0.191603 |
| BIL | 21 | 128 | 0.510938 |
| BIL | 60 | 120 | 0.847500 |
| BIL | 120 | 108 | 1.188889 |

These are forecasts issued at multiple past origins, not the single locked
May experiment. Their periods and targets differ, so the tables are not
interchangeable. Overlapping origins are dependent observations. Empirical
band coverage is recorded in the CSV; high coverage can reflect wide ranges,
not accurate point predictions. A legacy one-step reliability score must not
be interpreted as demonstrated six-month forecasting skill.

## Formulas and thresholds

Let A be the actual close, C the previous close, V the traded share count,
and r_hat the model's predicted log return:

```text
Training target r = log(A / C)
Expected price P = C * exp(alpha * r_hat)
Signed deviation D = A - P
Absolute deviation d = abs(A - P)
Signed deviation (%) = 100 * (A - P) / P
Scaled volume v = V / 1,000,000
Anomaly score S = d / (v + 0.000001)
```

Alpha is selected using validation prices. The anomaly score is not a
probability and should not be compared against one universal stock-independent
number. The original score formula has not changed.

The initial liquidity and band thresholds are selected on validation proxy
labels using F0.5, precision and flag-rate tie-breaks. For an evaluated session,
the rolling liquidity threshold is the corresponding reference percentile of
the previous 252 scores; zero-volume scores are excluded and at least 60 valid
past scores are required. Otherwise the initial threshold is retained. The
reference percentile is constrained to 0.60-0.995. Band severity uses its
own past percentile, constrained to 0.95-0.995, with a minimum cutoff of 1.05.
The current observation never enters its own cutoff.

```text
T_t = quantile(previous valid scores, reference percentile)
Liquidity flag = (S_t >= T_t) AND (V_t > 0)
Final anomaly = liquidity flag OR calibrated prediction-band flag
```

Structural discount remains a separate diagnostic. It is not fair value, not
proof of undervaluation, and not automatically an anomaly. SHAP continues to
explain the anomaly-score surrogate, not the neural network's internal gates.

## Reproduce and demonstrate

```bash
python research/component1/evaluate_model_upgrade.py --epochs 18
python -m pytest research/component1/tests -q
```

Inspect `artifacts/upgrade_v2/one_step_comparison.csv`,
`horizon_holdout_comparison.csv`, `may_hindcast_summary.csv`, and the two
`*_market_insight.json` files. `run_metadata.json` records the run provenance.
The application still exports MongoDB history to a private temporary CSV and
calls `analyze_market_on_demand.py` for a fresh calculation on Analyze. The
upgrade artifacts are demonstration evidence, not cached live results.

For a demonstration, show the selected rate/blend, horizon calibration, actual
versus expected price, the applicable anomaly cutoff, and the run ID/data date.
Explain why choosing the baseline is an evidence-based result rather than
forcing an attractive rising forecast. Components 2-4 and the UI were not changed.

## Remaining research work

- Record new dated forecasts now and assess them after their target dates.
  Previous known outcomes cannot establish new prospective accuracy.
- Obtain independently verified anomaly/event labels; stress windows and
  numeric tail rules remain proxies, not verified market causes.
- Validate corporate-action adjustments and data freshness against exchange
  records; no automatic split adjustment or fabricated live price was added.
- Test more stocks, crises and non-overlapping origins. The tests exercise
  common edge cases, not every possible market regime.
- Evaluate explanation usefulness with investors. Model consistency and error
  improvement alone do not establish human understanding or investment value.

## Methodological references

The separation of training and evaluation follows
[scikit-learn's leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).
Forecast origins follow the time-ordered evaluation principles in
[Forecasting: Principles and Practice](https://otexts.com/fpp3/toolbox.html).
Smooth L1 is a robust training-loss choice, not a proof of forecasting superiority;
see the [PyTorch loss documentation](https://docs.pytorch.org/docs/stable/generated/torch.nn.SmoothL1Loss.html).
