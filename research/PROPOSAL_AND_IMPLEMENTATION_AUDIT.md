# Proposal and Implementation Audit

## Purpose

This audit reconciles the four individual research proposals with the code that
is currently available. It separates implemented features, research evidence,
and claims that still require validation. The integrated product should behave
as one intelligent system; internal research stages must not be exposed as
separate member-owned features in the investor interface.

## Confirmed end-to-end scope

The proposals consistently describe this flow:

1. The user selects a Colombo Stock Exchange company.
2. Historical price, volume, volatility, and related market features are
   evaluated for trend, expected movement, unusual deviation, and risk.
3. A company financial report is converted into structured, traceable company
   information and an investor-friendly explanation.
4. relevant company, local-market, macroeconomic, and global-event context is
   collected and classified.
5. The independent outputs are combined into one plain-language, non-advisory
   explanation of what is happening, why it may be happening, uncertainty, and
   risk.
6. The presentation strategy is evaluated with non-expert investors, not merely
   displayed as a collection of charts.

For the current application milestone, the report upload is treated as required,
following the latest integrated workflow requirement. The investor-facing input
screen therefore contains only stock selection, PDF upload, and Analyze.

## Stage 1: Market behaviour, forecasting, and anomaly explanation

### Proposal requirement

The proposal requires OHLCV data preparation, time-series and regression-based
pattern learning, anomaly detection, factor explanation, interaction analysis,
explanation consistency over time, an integration API, and both technical and
usability evaluation.

### Current evidence

- The main research pipeline implements expected-price modelling, deviation- and
  liquidity-aware anomaly scores, prediction-band signals, risk levels, factor
  explanations, stability measures, and a forecast ensemble.
- Timestamped three-month forecasts exist for JKH and BIL.
- A reproducible out-of-sample validation notebook now compares those locked
  forecasts with 57 later CSE observations per stock.
- The upward scenarios did not validate. A no-change baseline produced lower
  error for both stocks. This negative result must be retained in the thesis and
  used to motivate recalibration.

### Missing or incomplete

- A timestamped third-stock forecast was not found.
- The current locked forecast artifact is 60 business days; separate validated
  4-day, 1-month, 3-month, and 6-month runtime outputs are not yet available.
- Forecast and anomaly quality has not yet been evaluated across enough stocks,
  regimes, and horizon-specific rolling windows.
- Explanation consistency and investor usability need formal reported results,
  not only implementation code.

### Acceptance criteria

- Each displayed horizon names its as-of date, target date, point estimate,
  interval, direction, and reliability based on a horizon-specific backtest.
- A baseline is always reported internally, and an advanced forecast is not
  promoted when it does not beat that baseline.
- Anomaly output includes actual price, expected price, signed deviation,
  standardized score, threshold, side, and liquidity context.
- Forecast confidence and anomaly confidence remain distinct.

## Stage 2: Financial-report understanding

### Proposal requirement

The proposal requires a dataset of at least 100 documents, at least 85% PDF text
extraction accuracy, at least 80% precision for indicators/ratios/risks, contextual
retrieval, grounded explanations, structured downstream signals, and model/prompt
benchmarking.

### Current evidence

- The available code extracts PDF pages, builds retrieval context, compares prompt
  variants, and validates a JSON schema.
- Its unit tests pass.
- A runtime adapter now checks that the report matches the selected company and
  verifies each returned quote against a specific extracted PDF page.

### Missing or incorrect

- The saved prompt experiment's best overall score is approximately 0.169 and
  its source-faithfulness score is zero. It therefore does not support a claim
  that the current prompt is accurate or grounded.
- Several saved outputs contain missing or malformed evidence.
- The proposal's 100-document dataset and 85%/80% target results are not present
  as reproducible evaluation artifacts.
- Existing unit tests check software behavior but do not demonstrate financial
  extraction accuracy.

### Acceptance criteria

- A response is marked complete only when important claims have exact page-level
  evidence; otherwise it is marked needs review.
- Scanned PDFs are routed to OCR or reported as unsupported, never silently
  summarized from insufficient text.
- The selected company must match the uploaded report.
- A labelled evaluation set must report field-level precision, recall, F1, text
  extraction quality, and unsupported-claim rate.

## Stage 3: News, sentiment, and external context

### Proposal requirement

The proposal describes company and market news collection, NLP sentiment/event
classification, macroeconomic context, technical evaluation using accuracy,
precision/recall/F1, and integration with the other research outputs.

### Current evidence

- The available code contains MarketAux, RSS, and web-source collectors,
  company alias matching, market-impact keywords, deduplication, and sentiment
  analysis utilities.
- Local-market terms cover inflation, interest rates, exchange rates, the IMF,
  oil/fuel, trade, war, and geopolitical events.

### Missing or incorrect

- Several controller/service files are empty, and this work is not connected to
  the main application.
- The configured external company symbols require verification against the data
  provider.
- Keyword detection of oil, gold, inflation, or war is not evidence of how a
  factor affects a particular stock.
- No reproducible labelled test report was found for accuracy, precision, recall,
  F1, freshness, source coverage, or company relevance.
- A quantitative claim of causality between a global factor and a stock would be
  unsupported by the present implementation.

### Acceptance criteria

- Articles are filtered for the selected company or clearly labelled as
  market-wide context, with source, timestamp, URL, and relevance reason.
- Duplicate and stale articles are removed, and source failures are visible in
  diagnostics.
- Sentiment/event metrics are evaluated on a manually labelled CSE-oriented test
  set.
- Commodity/macro price relationships are described as historical associations,
  with date range, sample size, lag, and uncertainty; no causal language is used
  without a causal research design.

## Stage 4: Unified insight and human interpretability

### Proposal requirement

The proposal requires one dashboard that integrates all upstream outputs,
multiple explanation variants for the same insight, and comparative evaluation
using comprehension, SUS, FICS, adapted NASA-TLX, task completion, trust, and
think-aloud analysis followed by iterative refinement.

### Current evidence

- The current frontend contains an investor workspace and a dashboard-shaped
  result screen.

### Missing or incorrect

- The current result screen contains hard-coded confidence, risk, sentiment, and
  status text. These are placeholders and must not be presented as generated
  research results.
- The screen exposes internal stage names and technical terminology despite the
  product requirement to present one black-box decision-support experience.
- No explanation-variant experiment, participant dataset, statistical comparison,
  or iterative evaluation record was found.

### Acceptance criteria

- Every displayed result is returned by one versioned analysis response; no
  hard-coded confidence or risk claims remain.
- The primary output uses plain language, separates observation from uncertainty,
  cites report/news evidence, and includes a non-advisory statement.
- Alternative explanation formats are evaluated using a documented participant
  protocol and the proposal's comprehension, usability, trust, and cognitive-load
  measures.

## Unified response contract

The integrated API should store a short-lived analysis record containing:

- selected stock and analysis timestamp;
- market forecast horizons and anomaly/deviation evidence;
- report extraction status, structured findings, and page evidence;
- relevant news/events and external-factor context with sources;
- data freshness and per-stage quality warnings;
- one fused plain-language overview, potential, key risks, drivers, uncertainty,
  and explicit non-advisory note.

If a required stage fails, the system must return a partial/needs-review result
with the missing evidence named. It must not replace missing evidence with a
confident generated statement.

## Research conclusion

The proposed integrated workflow is supported by the four proposals, but the
current repository does not yet provide enough evidence to claim that all four
research stages are validated. Stage 1 has the strongest implementation and now
has honest out-of-sample forecast evidence. Stages 2 and 3 require labelled,
source-grounded evaluation, while Stage 4 requires an actual human
interpretability study. These are research obligations, not only UI tasks.

