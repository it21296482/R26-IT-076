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
6. Stock behaviour and global financial indicators are combined into an
   explainable LOW/MEDIUM/HIGH market-risk classification.

For the current application milestone, the report upload is treated as required,
following the latest integrated workflow requirement. The investor-facing input
screen therefore contains only stock selection, PDF upload, and Analyze.

## Novelty and integration matrix

| Stage | Proposal-level novelty | What is integrated now | Research evidence still required |
| --- | --- | --- | --- |
| Market behaviour | Explainable, anomaly-aware CSE modelling that combines expected movement, liquidity-aware deviation, factor contribution, interaction analysis, and consistency over time. | Fresh 4-day, 1-month, 3-month, and 6-month paths; uncertainty ranges; signed deviation; anomaly score and direction; baseline comparison; factor contribution and explanation-stability outputs. | Explicit factor-interaction validation, broader multi-stock/regime testing, and formal usability evidence. |
| Financial reports | Localized, retrieval-enhanced interpretation that converts unstructured reports into grounded financial-health, growth, and risk signals. | Annual/quarterly PDF handling, company/date checks, structured findings, contextual extraction, and page-verified quotes in the Analyze workflow. | Proposal-scale document corpus and labelled extraction, grounding, and reliability results. |
| External context | Event-driven sentiment and news understanding integrated with market context rather than presented as a generic feed. | Selected-company, local, and global news; deduplication; event/sentiment labels; ASPI comparison; gold, oil, VIX, and USD/LKR associations and business channels. | Labelled CSE sentiment/event metrics, source-coverage evidence, and monitored provider reliability. |
| Explainable global-market risk | A stock-risk classifier that combines stock behaviour with Gold, Oil, and VIX and explains why the selected risk level was produced. | A reproducible BIL/JKH Random Forest, chronological holdout, stock-only ablation, and corrected multiclass SHAP adapter produce current-risk and driver meanings inside the unified Analyze result. | Broader CSE stock coverage, rolling-window temporal stability, and independent validation of the current-risk definition. |

## Fourth-branch integration decision

The later component description supplied after the updated proposal defines the
fourth contribution as an explainable financial-market risk engine. It therefore
supersedes the earlier human-centred explanation description for integration
purposes. The `origin/IT22547088` branch was reviewed file by file rather than
merged wholesale.

The trained Random Forest, stock encoder, supporting dataset, and model-aligned
risk logic were preserved under `research/component4`. The branch's separate
Flask server, separate `/risk` React page, duplicate authentication/database
configuration, hard-coded service URLs, exposed credentials, and recommendation-
style output were not merged because they conflict with the current MERN
architecture and one-page non-advisory workflow.

The adapter also corrects a material multiclass SHAP indexing error in the branch:
the model returns an instance-by-feature-by-class array, so contributions must be
read across all features for the predicted class. The current runtime refuses
unsupported stocks instead of silently substituting another company.

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
  labels; an ASPI comparison; and stock-aligned gold, oil, VIX, and USD/LKR
  context.
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

## Stage 4: Explainable global-market risk impact

### Revised requirement

The latest supplied component definition requires a LOW/MEDIUM/HIGH stock-risk
classification from historical stock behaviour plus Gold, Oil, and VIX. A
Random Forest performs classification and SHAP explains the main factors that
influenced the selected class. The output must contribute to the same unified
dashboard rather than becoming a separate recommendation page.

### Current evidence

- The preserved branch artifact remains available for provenance, while the live
  model is a reproducible 300-tree `RandomForestClassifier` supporting BIL and
  JKH with classes 0/1/2 mapped to LOW/MEDIUM/HIGH.
- Runtime inputs include price, volume, averages, recent return, drawdown,
  relative variability, unusual volume, Gold, Oil, VIX, their recent changes,
  and encoded stock identity.
- The risk stage consumes the selected stock's latest MongoDB history and reuses
  the dated global indicators returned by the external-context stage.
- The corrected SHAP adapter returns top overall drivers and separately explains
  whether Gold, Oil, and VIX supported or partly offset the predicted class.
- A chronological 80/20 holdout achieved 85.98% accuracy, 0.867 balanced
  accuracy, and 0.859 macro-F1 across 1,320 BIL/JKH test observations.
- The majority baseline macro-F1 was 0.125. A stock-only ablation reached 0.828,
  so global indicators added 0.031 macro-F1 in this experiment.
- Risk is displayed inside the same first-page plain-language result and is also
  passed into final evidence fusion. Technical model terminology is restricted
  to the protected research demonstration and documentation.

### Missing or incorrect

- The risk labels describe a documented current observable market-risk index;
  they are not ground-truth future losses or investment-return outcomes.
- Holdout metrics measure classification fidelity to that risk definition, not
  future-price forecasting skill.
- Only BIL and JKH are evaluated. Other stocks remain unsupported until they are
  added to training and chronological validation.
- SHAP explains model behaviour; it does not establish that a factor caused the
  real-world stock risk.

### Acceptance criteria

- Every supported-stock result names the feature date, risk class, main drivers,
  global-factor direction, and model scope.
- Unsupported stock symbols return an explicit unavailable result; no proxy stock
  or fabricated risk label is allowed.
- Research reporting includes reproducible label construction, data split,
  class balance, baseline comparison, confusion matrix, precision, recall, F1,
  and out-of-sample performance.
- Ablation and temporal-stability tests demonstrate whether Gold, Oil, and VIX
  add measurable value beyond stock-only inputs. The first ablation is complete;
  rolling regime-specific stability remains outstanding.
- Model contribution is described as explanation, not causal proof or investment
  advice.

## Unified response contract

The integrated API should store a short-lived analysis record containing:

- selected stock and analysis timestamp;
- market forecast horizons and anomaly/deviation evidence;
- report extraction status, structured findings, and page evidence;
- relevant news/events and external-factor context with sources;
- explainable global-market risk level, drivers, factor dates, and model scope;
- data freshness and per-stage quality warnings;
- one fused plain-language overview, potential, key risks, drivers, uncertainty,
  and explicit non-advisory note.

If a required stage fails, the system must return a partial/needs-review result
with the missing evidence named. It must not replace missing evidence with a
confident generated statement.

## Research conclusion

The four stages are connected in the current end-to-end Analyze workflow, and
their distinct novelty is documented without exposing member ownership or model
internals in the investor interface. Integration is not the same as research
validation. Stage 1 has implementation and honest out-of-sample evidence but
still needs broader and interaction-specific validation. Stages 2 and 3 need
labelled, source-grounded evaluation. Stage 4 now has reproducible BIL/JKH
training, chronological performance, ablation evidence, and explainable live
output, but still needs independent risk-definition validation, rolling
stability, and broader CSE coverage. The shared
plain-language integration layer remains product behaviour rather than a fifth
research contribution.
