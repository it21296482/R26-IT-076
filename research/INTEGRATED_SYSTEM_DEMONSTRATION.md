# Integrated System Demonstration and Research Novelty

## Research purpose

The system gives a non-expert investor a complete, evidence-aware picture of a selected Colombo Stock Exchange company. It is decision support, not buying or selling advice. The investor-facing application deliberately hides implementation detail and shows meaning, uncertainty, potential, and risk in plain language.

## Four research contributions at a glance

| Research stage | Distinct novelty | Current integration boundary |
| --- | --- | --- |
| Market behaviour | Combines fresh multi-horizon price ranges with signed expected-price deviation, liquidity-aware anomaly direction, factor contribution, and explanation stability for the CSE. | Fresh forecasts, uncertainty, deviation, anomaly, baseline comparison, factor evidence, and stability evidence run in the live pipeline. Formal factor-interaction validation and broader multi-stock evaluation remain research work. |
| Financial-report understanding | Converts local quarterly or annual disclosures into structured growth, financial-health, and risk evidence while preserving page-level traceability and contextual meaning. | Company/date validation, report extraction, structured findings, and verified page quotes run in the live pipeline. Proposal-scale document accuracy and grounding targets still require a labelled evaluation set. |
| External context | Goes beyond a generic news feed by connecting dated company, market, and global events to sentiment, wider-market direction, measured factor association, and the selected company’s practical exposure. | News, event labels, ASPI comparison, and gold, crude-oil, and USD/LKR context run in the live pipeline. A labelled CSE sentiment/event evaluation remains outstanding. |
| Human-centred insight delivery | Treats presentation as a research problem: fuse multiple evidence types, compare alternative explanation formats, measure actual investor comprehension, and refine the interface from evidence. | The unified plain-language result and source-labelled supporting views are live. The comparative explanation-variant participant study and iterative refinement evidence are not yet complete and must not be claimed as validated. |

## Exact user and backend flow

1. The user signs in and selects one supported stock.
2. The user uploads the latest quarterly or annual report for that company. The upload is required.
3. The server checks that the PDF belongs to the selected company and that its reporting date is acceptably recent. A mismatched or stale report is rejected before analysis.
4. When the user clicks **Analyze**, the server starts the market, report, and external-context stages together.
5. Each stage returns a structured evidence package. A failed input is labelled unavailable; it is never guessed.
6. The integration stage receives those packages and produces one plain-language stock picture.
7. The result shows potential price paths, downside ranges, unusual movement evidence, company strengths and risks, relevant external context, and what could change the picture.
8. The integrated run is stored temporarily and automatically expires after 24 hours.

The API entry point is `server/src/controllers/analysisController.js`. It coordinates the first three analyses with `Promise.allSettled`, then calls the integration service only after those results are available.

## Stage 1: market behaviour and unusual movement

**Input:** all historical OHLC price and trading-volume rows currently stored in MongoDB for the selected symbol.

**What runs:** every Analyze click exports a fresh database snapshot to a private temporary CSV and runs the market research pipeline again. It estimates one 120-trading-session path and reports checkpoints at 4 trading days, 1 month, 3 months, and 6 months. For every checkpoint it returns a central estimate, favourable side of the measured 80% range, adverse side of the measured 80% range, and a wider 95% uncertainty range. The longer checkpoint is shown with explicit uncertainty and baseline caution.

The stage also compares actual and expected prices, calculates signed deviation, scores unusual behaviour while accounting for market liquidity, identifies whether the deviation is above or below expectation, and reports the selected warning threshold.

**Output:** a versioned JSON contract containing data cut-off date, fresh run ID, row count, horizons, uncertainty ranges, anomaly evidence, recent deviation history, and held-out test quality.

**Research novelty:** forecast potential and anomaly evidence are interpreted together. The system does not merely say that a price moved; it shows how far the observed price departed from its expected pattern, in which direction, how unusual that gap was, and how much uncertainty surrounds future paths. It also reports when a simple unchanged-price baseline performs better, preventing false confidence.

The underlying research pipeline also produces factor-contribution and explanation-stability evidence. Explicit interaction analysis between price, volume, and volatility still needs a documented validation artifact before it can be claimed as a completed research result.

**Validation boundary:** the locked forecasts created in May 2026 remain unchanged and are used only for out-of-sample research validation. Live user results are newly calculated from the latest stored history. Reproducibility means two runs with unchanged data may correctly produce the same values; a new run is not forced to be randomly different.

## Stage 2: financial-report understanding

**Input:** the latest company-matched annual or quarterly PDF uploaded by the user.

**What runs:** the report workflow extracts text, detects company identity, report type, and reporting period, then identifies decision-relevant financial and operational evidence. Common statement rows include revenue, gross profit and margin, operating result, group profit or loss, EPS, finance costs, operating cash flow, assets, equity, report-date NAV, and relevant segment changes. Every accepted claim retains its PDF page and source quote.

**Output:** a verified company summary, strengths, concerns, extracted facts, page-level evidence, and missing-field list.

**Research novelty:** unstructured reports become investor-readable evidence without losing traceability. This is not a generic summary: it prioritizes meaningful changes, distinguishes group results from shareholder-attributable results, supports both annual and quarterly structures, and refuses stale or company-mismatched documents.

The localized, context-aware report workflow is integrated. The proposal's document-count, extraction-accuracy, indicator-precision, and grounding targets still require reproducible labelled evaluation and are not implied by the live interface.

## Stage 3: external context and market factors

**Input:** stock-specific, local-market, and global financial coverage, plus time-aligned gold, crude-oil, USD/LKR, and selected-stock price histories.

**What runs:** the workflow collects dated relevant articles, removes duplicates, identifies event themes and language tone, and separates company-specific from broader-market context. It compares overlapping daily returns for each external factor and the selected stock, then explains the practical business channel for that company. For example, oil may affect transport and operating costs, while USD/LKR may affect import costs, foreign-currency exposure, or translated earnings.

**Output:** relevant dated articles, context labels, factor movements, observed association strength, overlap count, explanatory share, business channel, and warnings.

**Research novelty:** external information is not shown as an unrelated news feed. It is filtered for the selected stock and translated into stock-specific business meaning. The output explicitly says that correlation and event timing are context, not proof of causation.

The live workflow includes dated company/local/global coverage, event and sentiment labels, ASPI comparison, and gold, crude-oil, and USD/LKR associations. Its research metrics still need to be established on a manually labelled CSE-oriented test set.

## Stage 4: integrated human-readable stock picture

**Input:** the structured evidence from stages 1-3.

**What runs:** the integration layer balances central and adverse price paths, unusual deviations, verified company strengths, report risks, current events, external-factor exposure, data limitations, and conditions that could change the outlook.

**Output:** one headline and plain-language overview, a balanced evidence label, supporting evidence, risk evidence, potential, uncertainty, and a non-advisory statement. Detailed source-labelled sections remain available below the summary for review.

**Research novelty:** the final contribution is not another static chart. It is a human-centred explanation framework that combines multiple evidence types, supports comparison of visual-only, visual-plus-explanation, factor, event, and risk presentation strategies, measures actual investor understanding, and uses those findings to refine the interface.

The current application integrates the evidence and presents one plain-language result with supporting visual and contextual views. Comparative participant testing using comprehension, usability, trust, task-completion, and cognitive-load measures remains formal research work; it is not represented as completed validation.

## Recommended live viva demonstration

1. In the admin console, show the BIL and JKH historical row counts and latest trading dates.
2. Sign in as a normal user and select `BIL.N0000`.
3. Upload the 30 June 2026 BIL quarterly report.
4. Explain that company and date validation occurs before Analyze is enabled.
5. Click Analyze once and show the backend logs starting the three evidence stages.
6. On the result, show the unique fresh market run ID and current database cut-off date.
7. Show central, favourable, and adverse paths at 4 days, 1 month, 3 months, and 6 months.
8. Show actual versus expected price, signed deviation, anomaly score, and threshold.
9. Show the BIL report evidence: 45% revenue growth, gross-margin improvement, operating recovery, narrower loss, segment turnarounds, cash-flow improvement, balance-sheet expansion, and the report-date NAV context.
10. Show relevant dated news and the oil, gold, and USD/LKR business channels, emphasizing that association does not prove cause.
11. Finish with the integrated plain-language picture and its non-advisory statement.

## Questions likely to be asked

**Does clicking Analyze reuse an old prediction?**  
No. The live flow reads the latest MongoDB history and executes a fresh deterministic run. Locked files are retained only to validate the earlier research forecast.

**Why can two fresh runs show the same values?**  
The workflow is intentionally reproducible. If the data and configuration have not changed, the mathematically correct result can be identical.

**Are favourable and adverse lines guaranteed best and worst prices?**  
No. They are the upper and lower sides of a measured 80% uncertainty range. The UI labels them as scenarios, not price targets.

**Can a war or news event be claimed as the cause of an anomaly?**  
Only when there is direct evidence can the event be described as business impact. Date overlap and correlation provide relevant context but do not prove how much of a share-price move the event caused.

**How should the six-month price be explained?**

It is the 120th trading-session checkpoint of the freshly calculated path. It is a research estimate with favourable and adverse uncertainty ranges, not a guaranteed target, and should be interpreted more cautiously than a shorter horizon.

**How is hallucination controlled?**  
Missing evidence is labelled missing, report claims retain source pages and quotes, stale/mismatched reports are rejected, external relationships are described as associations, and the integration layer receives structured evidence rather than permission to invent facts.

## Demonstration checklist

- MongoDB contains at least 300 valid rows for the selected stock.
- Latest trade date and company name are correct.
- The uploaded PDF is the newest available annual or quarterly report for that company.
- Python dependencies for all research workflows are installed.
- `MARKET_ANALYSIS_EPOCHS` and timeout are configured on the server.
- The result has a fresh run ID and current data cut-off date.
- All report claims shown in the viva have page-level source evidence.
- Uncertainty and the non-advisory statement remain visible.
