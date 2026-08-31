# Integrated System Demonstration and Research Novelty

## Research purpose

The system gives a non-expert investor one evidence-aware outlook for a selected
Colombo Stock Exchange company. It is decision support, not buying or selling
advice. The investor sees meaning, uncertainty, potential, and risk in plain
language rather than four disconnected technical outputs.

## Four research contributions at a glance

| Research stage | Distinct novelty | Current integration boundary |
| --- | --- | --- |
| Market behaviour | Combines fresh multi-horizon price ranges with signed expected-price deviation, liquidity-aware anomaly direction, factor contribution, and explanation stability for the CSE. | Fresh forecasts, uncertainty, deviation, anomaly, baseline comparison, factor evidence, and stability evidence run in the live pipeline. Formal factor-interaction validation and broader multi-stock evaluation remain research work. |
| Financial-report understanding | Converts local quarterly or annual disclosures into structured growth, financial-health, and risk evidence while preserving page-level traceability and contextual meaning. | Company/date validation, report extraction, structured findings, and verified page quotes run in the live pipeline. Proposal-scale document accuracy and grounding targets still require a labelled evaluation set. |
| News and sentiment | Goes beyond a generic feed by connecting dated company, CSE, economic, and relevant global news to event and sentiment evidence for the selected stock. | News retrieval, deduplication, event labels, and sentiment signals run in the live pipeline. A labelled CSE sentiment/event evaluation remains outstanding. |
| Explainable external-market risk | Combines stock behaviour with quantitative external-market conditions to classify current financial-market risk and explain which inputs supported or reduced that assessment. | ASPI and dated Gold, Oil, VIX, and USD/LKR context are collected here. A reproducible BIL/JKH Random Forest uses Gold/Oil/VIX and corrected multiclass SHAP explanation in the main Analyze workflow. The chronological holdout achieved 85.98% accuracy and 0.859 macro-F1; global indicators improved macro-F1 by 0.031 over the stock-only ablation. These metrics measure current-risk label fidelity, not future returns. |

## Exact user and backend flow

1. The user signs in and selects one supported stock.
2. The user uploads the latest quarterly or annual report for that company. The
   upload is required.
3. The server checks that the PDF belongs to the selected company and that its
   reporting date is acceptably recent. A mismatched or stale report is rejected.
4. When the user clicks **Analyze with latest prices**, the server requests the
   current official CSE trade summary once and upserts the latest row for every
   available MongoDB stock symbol.
5. Market modelling, report understanding, news/sentiment analysis, and
   external-market risk analysis start together. Each returns a separate
   structured evidence package; missing evidence is labelled unavailable and is
   never guessed.
6. The risk stage combines the selected stock's latest history with its own dated
   Gold, Oil, and VIX context.
7. The integration layer combines all four outputs into one plain-language stock
   picture.
8. The result appears below the inputs on the same `/dashboard` page. It starts
   with one takeaway, then provides source-labelled detail for review.
9. The integrated run is stored temporarily and expires automatically after 24
   hours.

The API coordinator is `server/src/controllers/analysisController.js`. It uses
one current-price refresh, runs the first three evidence stages concurrently,
runs the risk model when its shared inputs are available, and then calls the
integration service.

## Stage 1: market behaviour and unusual movement

**Input:** all historical OHLC price and trading-volume rows stored in MongoDB
for the selected symbol, including the latest CSE row refreshed at Analyze time.

**What runs:** every Analyze click exports a fresh database snapshot to a private
temporary CSV and reruns the market research pipeline. It estimates one
120-trading-session path and reports checkpoints at 4 trading days, 1 month, 3
months, and 6 months. Each checkpoint contains a central estimate, favourable
and adverse sides of the measured 80% range, and a wider 95% uncertainty range.

The stage also compares actual and expected prices, calculates signed deviation,
scores unusual behaviour while accounting for liquidity, identifies whether the
deviation is above or below expectation, and reports the warning threshold.

**Output:** data cut-off date, fresh run ID, row count, horizon paths, uncertainty
ranges, anomaly evidence, recent deviation history, held-out quality, factor
contribution, and explanation-stability evidence.

**Research novelty:** forecast potential and anomaly evidence are interpreted
together. The system reports how far the observed price departed from its
expected pattern, in which direction, how unusual the gap was, and how much
uncertainty surrounds future paths. It also reports when a simple unchanged-price
baseline performs better, preventing false confidence.

**Validation boundary:** locked May 2026 forecasts remain unchanged and are used
only for out-of-sample validation. Live results are newly calculated from the
latest stored history. Reproducibility means two runs with unchanged data may
correctly produce the same values.

## Stage 2: financial-report understanding

**Input:** the latest company-matched annual or quarterly PDF uploaded by the
user.

**What runs:** the report workflow extracts text, detects company identity,
report type, and reporting period, then identifies decision-relevant financial
and operational evidence. It checks revenue, profit and margin measures, group
result, EPS, finance costs, cash flow, assets, equity, NAV, and relevant segment
changes. Every accepted claim retains its PDF page and source quote.

**Output:** a verified company summary, strengths, concerns, extracted facts,
page-level evidence, and missing-field list.

**Research novelty:** unstructured reports become investor-readable evidence
without losing traceability. The workflow prioritizes meaningful changes,
distinguishes group results from shareholder-attributable results, supports
annual and quarterly structures, and refuses stale or company-mismatched files.

**Validation boundary:** the proposal's document-count, extraction-accuracy,
indicator-precision, and grounding targets still require reproducible labelled
evaluation and are not implied by the live interface.

## Stage 3: external context and market factors

**Input:** stock-specific, local-market, and global financial coverage, ASPI,
plus time-aligned gold, crude-oil, VIX, USD/LKR, and selected-stock histories.

**What runs:** the workflow collects dated relevant articles, removes duplicates,
identifies event themes and language tone, and separates company-specific from
broader-market context. It compares the selected share with ASPI to distinguish
a company-specific move from a wider-market move. It also measures overlapping
daily-return associations and explains the practical business channel for that
company.

**Output:** dated articles, context labels, ASPI comparison, factor movements,
association strength, overlap count, explanatory share, company-specific
business channel, and warnings.

**Research novelty:** external information is not an unrelated news feed. It is
filtered for the selected stock and translated into stock-specific business
meaning while clearly separating measured association from proven causation.

**Validation boundary:** event, sentiment, relevance, source coverage, and
freshness metrics still require a manually labelled CSE-oriented test set.

## Stage 4: explainable global-market risk impact

**Input:** the selected stock's latest close, volume, 10-session and 50-session
averages, recent return, drawdown, relative variability, unusual volume, stock
identity, and dated Gold, Oil, and VIX levels and recent changes collected by
this stage.

**What runs:** the reproducible CSE Random Forest returns LOW, MEDIUM, or HIGH
current risk for BIL or JKH. The transparent target combines observable price
variability, recent return and drawdown, unusual volume, VIX, and Gold/Oil
movement. The SHAP adapter evaluates contributions for the predicted class using
the correct multiclass output axis and explains whether global indicators
supported or partly offset the classification.

**Output:** risk level, plain explanation, main driver meanings, global-factor
meanings, factor dates, and an explicit model-scope statement. Raw model
internals remain in the research layer and are not exposed to investors.

**Research novelty:** the contribution does not stop at a risk label. It combines
stock behaviour with global financial conditions and explains why the model
produced that classification.

**Validation boundary:** both BIL and JKH are supported without a proxy. The
chronological 80/20 holdout contains 1,320 observations and reports 85.98%
accuracy, 0.867 balanced accuracy, and 0.859 macro-F1. The majority baseline
macro-F1 is 0.125; removing Gold/Oil/VIX lowers macro-F1 to 0.828. These results
validate fidelity to the documented current-risk categories, not future-loss or
investment-return prediction. Broader CSE coverage and temporal stability across
additional regimes remain future research.

## Shared integration layer: one plain-language outlook

**Input:** the four structured evidence packages.

**What runs:** the integration layer balances central and adverse price paths,
unusual deviations, verified company strengths, report risks, current events,
ASPI direction, external-factor exposure, explainable risk, data limitations,
and conditions that could improve or weaken the outlook.

**Output:** one headline and overview, a balanced evidence label, supporting
evidence, risk evidence, potential, uncertainty, and a non-advisory statement.
The same page retains source-labelled sections so an examiner can inspect how
the final takeaway was formed.

This layer is shared product integration. It should not be presented as a fifth
research component or as a replacement for any of the four contributions.

## Recommended live viva demonstration

1. In the protected admin console, show JKH historical row count, current data
   date, and the documented four-stage workflow.
2. Sign in as a normal user, select `JKH.N0000`, and upload its latest quarterly
   or annual report.
3. Click **Analyze with latest prices** once and keep the backend terminal visible.
4. Point out the official CSE refresh log, followed by all four research stages
   starting together.
5. Show that the news/sentiment stage returns event evidence while the separate
   risk stage returns quantitative external-market context and the explained
   risk category, followed by the final integration log.
6. On the same page, start with the single plain-language takeaway.
7. Show fresh central, favourable, and adverse paths at 4 days, 1 month, 3
   months, and 6 months.
8. Show actual versus expected price, signed deviation, anomaly score, threshold,
   and whether the movement is above or below expectation.
9. Show page-verified report strengths and concerns.
10. Show dated news, ASPI comparison, factor business channels, and the
    explainable LOW/MEDIUM/HIGH risk card.
11. Finish with uncertainty, evidence limitations, and the non-advisory statement.

Either BIL or JKH can now demonstrate all four stages. Show that the risk card
describes current observable conditions and is separate from the future price
paths produced by stage 1.

## Questions likely to be asked

**Do all four stages run when Analyze is clicked?**
Yes. The price refresh happens first; market, report, and context run concurrently;
risk runs from the latest stock and shared global-factor inputs; then one
integration step combines all four outputs.

**Where does the data come from?**
Historical OHLCV comes from MongoDB, the latest row comes from the official CSE
trade summary, company evidence comes from the uploaded PDF, events come from
dated company/local/global sources, ASPI and market factors come from time-aligned
market histories, and Gold/Oil/VIX feed both context and risk interpretation.

**Why is there no separate risk page?**
The research output is one stock picture for a non-expert investor. A separate
page would fragment the evidence and create two competing conclusions. The risk
engine remains independently testable in the backend but contributes to the
same first result page.

**Does clicking Analyze reuse an old prediction?**
No. The live market workflow reads the latest MongoDB history and executes a
fresh deterministic run. Locked files are retained only to validate earlier
research forecasts.

**Why can two fresh runs show the same values?**
The workflow is intentionally reproducible. If data and configuration have not
changed, the mathematically correct result can be identical.

**Are favourable and adverse paths guaranteed targets?**
No. They are sides of a measured uncertainty range, not guaranteed prices.

**Does SHAP prove that Gold, Oil, or VIX caused the stock risk?**
No. It explains how those feature values influenced this classifier's output.
Historical association, model contribution, and real-world causation are
different claims and remain clearly separated.

**How is hallucination controlled?**
Missing evidence is labelled missing, report claims retain pages and quotes,
stale or mismatched reports are rejected, external relationships are described
as associations, unsupported risk stocks are refused, and the final layer may
only use structured upstream evidence.

## Demonstration checklist

- MongoDB contains at least 300 valid rows for the selected stock.
- The uploaded PDF is the newest available annual or quarterly report.
- Python dependencies for all research workflows are installed.
- `MARKET_ANALYSIS_EPOCHS`, market timeout, and risk timeout are configured.
- The CSE refresh reports the current trade date or an explicit warning.
- The result has a fresh run ID and current market-data cut-off date.
- Report claims shown in the viva have page-level source evidence.
- BIL or JKH is used because both are included in the evaluated CSE risk model.
- Uncertainty and the non-advisory statement remain visible.
