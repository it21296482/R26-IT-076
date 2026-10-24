# CSE Listing Coverage: 18 October 2026

## Scope

All 302 securities returned by CSE's alphabetical directory are selectable for
analysis. Listing count is not company count: voting and non-voting classes are
separate securities. Preparation runs only for the selected security, after the
user supplies its genuine latest financial report.

## Source Audit

A read-only audit checked all 302 listings against up to 5,000 actual daily
TradingView CSELK observations and recent official CSE daily high/low records.
It did not insert 302 datasets into MongoDB or claim 302 trained-model evaluations.

| Result | Listings |
| --- | ---: |
| Meets forecast data/activity checks | 247 |
| Insufficient observations or recent trading activity | 16 |
| Conflicting or insufficient current-basis corroboration | 28 |
| Official daily history unavailable | 7 |
| Stale completed trading history | 3 |
| Secondary daily history unavailable | 1 |
| Total checked | 302 |

Receipt: `output/cse-listing-history-audit.json`, captured at
2026-10-18 13:12 UTC. Re-run `npm run audit:stock-coverage -- --all` from `server/`
to produce a new dated result. External source availability can change.

These counts describe source eligibility, not prediction accuracy. Original
JKH/BIL locked validation claims remain unchanged. Older secondary observations
are explicitly split-adjusted and are not independently verified exchange totals.
Recent official closing prices and total volumes are used only where the daily
high/low prices agree; no inferred adjustment factor or synthetic opening is used.

## Actual Additional-Security Runs

- Commercial Bank non-voting (`COMB.X0000`): 3,304 valid sessions; fresh four-day,
  one-month, three-month and six-month forecasts, deviations and anomaly score.
  Its own fresh risk fit completed, with chronological label-agreement macro-F1
  0.775479 versus 0.140606 for the majority comparison.
- Dialog (`DIAL.N0000`): 3,392 valid sessions; the same four forecast horizons and
  anomaly workflow completed. Its separate risk fit completed, with chronological
  label-agreement macro-F1 0.802575 versus 0.118081 for the majority comparison.

The risk metrics assess the existing research-defined current-risk categories,
not future losses. Neither result is evidence of universally accurate forecasts.
Forecast caution flags and uncertainty ranges remain visible.

Private receipts: `output/live-stock-COMB.X0000.json` and
`output/live-stock-DIAL.N0000.json`. Source snapshots and preimages are under
`server/uploads/stock-preparation/`; risk fit evidence is under
`server/uploads/risk-runs/`. These files contain private runtime evidence and
must not be committed with credentials or user reports.

## Integration Regression

A genuine locally stored June 2026 JKH report was submitted through the running,
authenticated analysis API after these changes. It returned HTTP 201 in 87.3
seconds, with all four evidence stages and the unified explanation completed,
all four forecast horizons present, and no evidence warnings. Receipt:
`output/api-verification-JKH.N0000.json`. This verifies the existing integrated
workflow; it is not a substitute for supplying each additional company's report.

Regression results: 63 server tests, 68 Python tests across the research stages,
and 11 frontend tests passed (142 total). Frontend lint/build and both local
frontend/backend health checks also passed.

## Runtime Demonstration

1. Select any current CSE security and upload its latest genuine company report.
2. The backend confirms the directory identity and verifies the report before
   fetching history. The progress stream shows actual preparation/training stages.
3. The selected security's observations are sourced, reconciled and checked.
   Models use completed sessions, not unfinished current-day quotes.
4. Component 1 fits fresh models for expected price, anomaly/deviation checks and
   the four forecast horizons. No locked forecast or another company's data is used.
5. Component 2 reads the uploaded report; Component 3 collects relevant news;
   Component 4 builds external-factor evidence and fits a security-specific risk
   classifier for securities outside the preserved JKH/BIL artifact's coverage.
6. Outputs are combined into the existing single-page explanation. Missing
   evidence remains labelled; report/news insights do not manufacture a forecast.

New-series operational requirements remain 1,000 valid observations, 80 active
observations among the last 252, recent completed prices, and corroboration of
the current price basis. These are conservative guards, not validated universal
liquidity thresholds. Newly listed, suspended and unsupported securities cannot
honestly be promised complete four-horizon or three-class risk results.

Fresh model work is bounded to two analyses at once, with a small waiting queue
and one active request per user. Historical observations are fetched on demand;
unchanged rows are not rewritten. Storage/audit retention and provider data-use
permissions must be reviewed before wider public deployment.
