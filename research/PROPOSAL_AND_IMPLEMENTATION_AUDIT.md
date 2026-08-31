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

## Novelty and integration matrix

| Stage | Proposal-level novelty | What is integrated now | Research evidence still required |
| --- | --- | --- | --- |
| Market behaviour | Explainable, anomaly-aware CSE modelling that combines expected movement, liquidity-aware deviation, factor contribution, interaction analysis, and consistency over time. | Fresh 4-day, 1-month, 3-month, and 6-month paths; uncertainty ranges; signed deviation; anomaly score and direction; baseline comparison; factor contribution and explanation-stability outputs. | Explicit factor-interaction validation, broader multi-stock/regime testing, and formal usability evidence. |
| Financial reports | Localized, retrieval-enhanced interpretation that converts unstructured reports into grounded financial-health, growth, and risk signals. | Annual/quarterly PDF handling, company/date checks, structured findings, contextual extraction, and page-verified quotes in the Analyze workflow. | Proposal-scale document corpus and labelled extraction, grounding, and reliability results. |
| External context | Event-driven sentiment and news understanding integrated with market context rather than presented as a generic feed. | Selected-company, local, and global news; deduplication; event/sentiment labels; ASPI comparison; gold, oil, and USD/LKR associations and business channels. | Labelled CSE sentiment/event metrics, source-coverage evidence, and monitored provider reliability. |
| Human-centred delivery | A comparative explanation framework that measures comprehension, trust, usability, and cognitive load, then refines how integrated insights are communicated. | One versioned result combines all evidence into a plain-language overview, price/risk views, report evidence, events, factor context, uncertainty, and a non-advisory note. | Multiple explanation-variant experiment, participant data, FICS/SUS/adapted NASA-TLX/task/think-aloud results, statistical comparison, and documented iterative refinement. |

## Fourth-branch integration decision

The unmerged `origin/IT22547088` branch was reviewed against the updated fourth
proposal. Its `/risk` route and separate Python service implement another
standalone market-risk predictor with manual indicator inputs and recommendation-
style output. That is not the proposal's human-centred explanation and
interpretability contribution, and it duplicates the first research stage.

The branch was therefore not merged into the product. The proposal-aligned part
is integrated through the existing unified analysis result and protected research
demonstration. The explanation-variant comparison, participant measurement, and
iterative refinement remain research evaluation work rather than hidden or
falsely completed features.

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
- Every live Analyze request now reruns the market pipeline from the selected
  stock's latest MongoDB history and returns 4-day, 1-month, 3-month, and
  6-month checkpoints with central, favourable, and adverse ranges.
- Timestamped three-month forecasts exist for JKH and BIL.
- A reproducible out-of-sample validation notebook now compares those locked
  forecasts with 57 later CSE observations per stock.
- The upward scenarios did not validate. A no-change baseline produced lower
  error for both stocks. This negative result must be retained in the thesis and
  used to motivate recalibration.

### Missing or incomplete

- A timestamped third-stock forecast was not found.
- The live horizons exist, but independent horizon-specific validation is not
  yet available for all four checkpoints.
- A reproducible, explicitly reported factor-interaction analysis was not found;
  factor contribution and stability should not be described as interaction
  validation.
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
- The report adapter is called directly by the main Analyze workflow, and its
  structured evidence is passed into the unified explanation.

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
- The main Analyze workflow now calls a failure-aware external-context adapter
  that returns selected-company, local, and global articles; sentiment and event
  labels; an ASPI comparison; and stock-aligned gold, oil, and USD/LKR context.
- Each external factor includes its overlap count, association strength,
  explanatory share, business channel, and an explicit non-causal warning.

### Missing or incorrect

- The preserved classifier and current production adapter use different
  sentiment paths; their relationship and selected production method need to be
  justified in the methodology.
- Event/keyword detection and statistical association do not prove how much an
  external factor caused a particular stock movement.
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

- The main controller runs the first three evidence stages concurrently, passes
  their structured outputs into one integration stage, and stores one
  short-lived versioned analysis result.
- The investor result renders returned price paths, anomaly/deviation evidence,
  verified report strengths and concerns, dated events, external-factor
  context, one plain-language conclusion, uncertainty, and a non-advisory note.
- Internal research ownership and implementation terminology are kept out of
  the investor-facing workflow; the four-stage explanation is restricted to the
  protected administration demonstration.

### Missing or incorrect

- No explanation-variant experiment, participant dataset, statistical comparison,
  or iterative evaluation record was found.
- The current interface presents several evidence views, but this is not the
  same as a controlled comparison of the proposal's alternative explanation
  strategies.

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

The four stages are connected in the current end-to-end Analyze workflow, and
their distinct novelty is now documented without exposing member ownership in
the investor interface. Integration is not the same as research validation.
Stage 1 has implementation and honest out-of-sample evidence but still needs
broader and interaction-specific validation. Stages 2 and 3 need labelled,
source-grounded evaluation. Stage 4 has a working unified presentation layer but
still requires the proposed explanation-variant and human-interpretability
study. These are research obligations, not only UI tasks.
