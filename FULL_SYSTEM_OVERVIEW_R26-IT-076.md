# AI-Powered Stock Market Insight Generator for the Colombo Stock Exchange

## Complete System Overview

**Project:** R26-IT-076  
**Scope:** The working stock-analysis application and its four research contributions  
**Implementation reviewed:** 24 October 2026

This document describes the current implementation. It separates implemented behaviour, conditional capabilities and research limitations. It is not a new live-service audit or a claim that every external source is currently reachable.

## 1. The System in Plain English

The system helps a non-expert investor understand a selected Colombo Stock Exchange company without having to interpret price charts, financial statements, news and global-market indicators separately.

The user selects a stock, uploads the company's latest quarterly or annual financial report, and starts an analysis. The application brings together four kinds of evidence:

1. How the stock's price and trading activity are behaving.
2. What the company's financial report says about its performance.
3. What relevant news and sentiment suggest about its surroundings.
4. How wider financial conditions relate to its current market risk.

It combines these into one understandable stock outlook, supported by detailed evidence on the same page.

The intended result is a balanced picture of strengths, concerns, potential, unusual movement and uncertainty. The user makes the investment decision. The system does not issue buy, sell or hold instructions.

## 2. The Problem It Addresses

A price chart shows what happened, but does not by itself explain the company's condition or the context around the movement.

A company's revenue can improve while its share price falls. A market-wide decline can affect a company whose operations remain strong. A price increase can also occur alongside weak cash flow or elevated external risk.

The application therefore avoids treating one signal as a complete answer. Its purpose is to connect market behaviour, company performance, reported events and financial-market risk while keeping the evidence and its limitations visible.

It aims to answer:

- What is happening to the stock?
- Is the movement unusual relative to the measured recent pattern?
- What is improving or weakening inside the company?
- What relevant events are being reported?
- Is the movement shared with the broader market?
- What external pressures or favourable conditions should be considered?
- What future price ranges does the tested historical pattern suggest?
- What remains uncertain or unavailable?

These are decision-support questions, not guarantees that every real-world cause can be identified.

## 3. User Experience

### 3.1 Before Signing In

The public website explains the product's value, introduces the analysis process and provides separate sign-in and account-registration pages.

The admin entry is not linked from the ordinary public navigation.

### 3.2 After Signing In

The user enters the workspace and:

1. Selects a company by full name and exact security code, such as John Keells Holdings PLC (JKH.N0000).
2. Uploads its latest quarterly/interim or annual financial report as a PDF.
3. Clicks Analyze.
4. Follows the analysis progress indicator.
5. Reads the integrated result below the inputs on the same dashboard page.

The report is **required in the current application**, not optional.

The latest-price list is separate from the company selector. Positive percentage changes are green, negative changes are red, and unchanged or unavailable changes remain neutral.

### 3.3 The Result

The result is organised around one overall outlook with supporting sections:

- Plain-language combined summary.
- Company strengths and concerns.
- Expected versus observed price and unusual-movement evidence.
- Potential price paths at four horizons.
- Dated news and sentiment.
- External-factor relationships and explained current market risk.
- Conditions that could improve or weaken the picture.
- Missing evidence, limitations and a non-advisory statement.

The five exploration views are price behaviour, company report, news/sentiment, external-market risk and overall insight. These are views of the analysis, **not five independent research components**.

## 4. Overall Architecture

```text
React user interface
        |
        v
Express API: authentication, validation and analysis coordination
        |
        +--> MongoDB: accounts, history, reports and temporary results
        |
        +--> Price refresh and selected-security history preparation
        |
        +--------------------+-------------------+-------------------+
        |                    |                   |                   |
        v                    v                   v                   v
Component 1             Component 2          Component 3         Component 4
Price behaviour         Financial report     News/sentiment     External risk
and anomalies           understanding        and events         and explanations
        |                    |                   |                   |
        +--------------------+-------------------+-------------------+
                                      |
                                      v
                         Evidence-based integration
                                      |
                                      v
                          One plain-language outlook
                                      |
                                      v
                      Optional Sinhala/Tamil translation
```

The platform uses MongoDB, Express, React and Node.js, with Python research workflows invoked by the backend.

The browser does not connect directly to MongoDB, train the research models or receive private provider credentials.

## 5. What Happens When Analyze Is Clicked

The coordinator is `server/src/controllers/analysisController.js`.

1. **Authenticate the user.** The server verifies the session and the user's access rights.
2. **Confirm the security.** The submitted symbol is checked against the current CSE company directory.
3. **Refresh available quotes.** The server requests the official CSE trade summary and refreshes available stored symbols. A failed request becomes a warning rather than a fabricated quote.
4. **Validate the report again.** The report must belong to the signed-in user and selected company. Its reporting type and period must pass the recency checks.
5. **Create a run record.** A processing analysis record is created with its own identifier and an expiry time.
6. **Prepare selected-stock history.** The backend checks existing history and, when needed, obtains and reconciles actual historical observations.
7. **Start the four evidence stages concurrently.** Market analysis, report understanding, news/sentiment and external-market risk run as separate tasks.
8. **Collect successes and failures independently.** The coordinator uses `Promise.allSettled` so one unavailable stage does not automatically discard all usable evidence.
9. **Combine the evidence.** The integration layer receives the structured outputs and creates one stock outlook.
10. **Save and display the result.** The response is recorded as completed, partial or failed according to the workflow outcome. Warnings remain visible.
11. **Translate on request.** A later language change translates displayed narratives without recalculating prices or retraining models.

Inside Component 4, external-factor collection precedes its risk assessment. Across the application, the four top-level stages run concurrently after shared preparation; they are not a serial chain of four separate pages.

The progress stream reports actual stage and model-training events. Its percentage is a stage-weighted progress indication, not a precise measurement of remaining processing time.

## 6. Component 1: Market Behaviour, Forecasting and Anomalies

### Purpose

Understand the selected stock's observed behaviour, estimate possible future price paths and identify departures from its expected recent pattern.

### Inputs

- Historical open, high, low and closing prices.
- Trading volume.
- Dates and source information.
- Derived price, momentum, volatility, range and relative-volume features.

Live training reads the selected security's available valid MongoDB history, using completed sessions rather than treating an unfinished current-day quote as a final training observation.

### Processing

The backend exports a fresh history snapshot to a private temporary file and invokes `research/component1/analyze_market_on_demand.py`.

The workflow:

- Checks and orders observations.
- Derives market features.
- Fits the expected-price workflow using chronological data splits.
- Compares expected and observed prices.
- Calculates signed and absolute deviations.
- Calculates the liquidity-aware anomaly score.
- Checks calibrated liquidity and prediction-band alerts.
- Adds persistent-pattern and pressure context separately.
- Produces factor explanations and explanation-stability evidence.
- Fits and selects forecasting methods separately for the four future horizons.

### Core Calculations

Let \(A_t\) be actual closing price, \(P_t\) expected price, and \(V_t\) shares traded:

\[
D_t=A_t-P_t,\qquad d_t=|A_t-P_t|,
\qquad \delta_t=100(A_t-P_t)/P_t.
\]

\[
S_t=\frac{d_t}{V_t/1{,}000{,}000+10^{-6}}.
\]

The final daily alert combines a valid-volume score crossing with an independently calibrated prediction-band severity crossing:

\[
a_t=\mathbf1\{(S_t\ge T_S\land V_t>0)\lor(B_t\ge T_B)\}.
\]

A threshold is selected using earlier calibration evidence; it is not a universal value for every stock. The current adaptive threshold uses past observations, not the observation being assessed or later data.

For a hypothetical expected price of LKR 24.00, actual price of LKR 19.80 and volume of two million shares, the signed deviation is -LKR 4.20, percentage deviation is -17.50%, and liquidity-aware score is approximately 2.10.

This example is a calculation, not a current quote or proof of fundamental value.

### Forecasts

The current horizons are 4, 21, 60 and 120 trading observations, displayed approximately as four trading days, one month, three months and six months.

The current candidate set includes persistence, ridge regression, random forest, extra trees and gradient boosting. Each horizon selects a candidate using purged chronological comparisons and refits from completed outcomes. The expected-price sequence model is a separate part of the workflow; it is incorrect to describe every future horizon as a direct output of that one model.

Outputs include a central path and empirical uncertainty ranges. Favourable/adverse sides are not guaranteed best/worst prices. Intermediate chart points are interpolated between trained horizon endpoints, not independently trained daily forecasts.

If an unchanged-price method wins validation, the system reports that result rather than forcing an artificial rise or fall.

### Outputs and Research Contribution

The stage supplies dated expected/actual prices, deviations, anomaly scores, thresholds, alert direction, forecast ranges, baseline comparisons, factor evidence and explanation stability.

Its distinctive research direction is the inspectable combination of participation-aware deviation, a separate band rule, pattern context and explanation-stability reporting for the studied CSE setting. Established forecasting and explanation algorithms are not claimed as new inventions.

### Important Boundaries

- No daily anomaly does not mean no sustained decline or external pressure.
- An expected-pattern price is not a fair-value estimate.
- Explanations describe an approximation of the anomaly score, not proven real-world causes.
- Fresh fitting does not guarantee that forecasts will improve.
- Original JKH/BIL forecast comparisons did not beat an unchanged-price baseline.
- Archived proxy-label leakage and limited positive-event counts restrict anomaly-performance claims.

Full formulas, results and improvements are in [the Component 1 report](research/component1/Component_1_Conclusion_Formulas_and_Improvements_IT21296482.md).

## 7. Component 2: Financial-Report Understanding

### Purpose and Input

Convert a company-matched quarterly/interim or annual PDF into understandable company-performance evidence.

### Validation

The report is checked both at upload and before analysis for:

- Ownership by the signed-in user.
- Selected-company identity.
- Recognisable reporting type and period.
- Acceptable recency under the reporting-period rules.
- Availability and readability of the saved file.

These checks use detected report information and recency rules. They do not independently prove that the uploaded PDF is the newest document published anywhere.

### Extraction and Interpretation

The runtime extracts report text and relevant statement/operational evidence, including available:

- Revenue, gross profit and operating profit.
- Margins, group results and shareholder-attributable results.
- Earnings per share and financing costs.
- Operating cash flow.
- Assets, equity and net asset value.
- Segment changes, operating improvements, expansion and milestones.
- Reported weaknesses, risks and missing information.

Accepted findings retain page references and supporting quotations. Important distinctions, such as group profit versus profit attributable to shareholders, should not be collapsed into one ambiguous number.

### Research Contribution

The research package compares ten prompt strategies using a shared output structure and source evidence. The designs cover basic extraction, analyst role, structured output, grounding, verification, ratios, risk, beginner explanations, examples and a hybrid approach.

Evaluation considers coverage, numerical accuracy, semantic similarity, source faithfulness, investor relevance and hallucination penalties.

This benchmark is an offline research exercise. Clicking Analyze does **not** rerun all ten prompt experiments.

### Runtime Outputs and Limits

The stage returns an investor-readable company summary, strengths, concerns, structured facts, page evidence and missing-field warnings.

A deterministic evidence-based summary can be produced without a cloud model. Optional language-model wording is checked before acceptance. Text-poor scans and complex tables can still limit extraction; OCR is not enabled by default. Page references and automated checks do not guarantee that every important report fact was found.

Implementation: `component_2/`, `server/src/services/reportInsightService.js` and `server/src/services/reportValidationService.js`.

## 8. Component 3: News, Events and Sentiment

### Purpose

Show what is being reported about the company and market, and provide dated event/sentiment context around the stock.

### Current Live Processing

The integrated adapter requests relevant company, Sri Lankan market, global/geopolitical and disaster/recovery news through configured searches.

It:

- Collects article titles, available descriptions, URLs, source names and dates.
- Removes duplicates.
- Balances company and wider-market coverage.
- Assigns relevance scopes and event categories.
- Calculates positive, negative or neutral sentiment.
- Records collection time, source coverage and warnings.

The current integrated sentiment path uses transparent finance-language term scoring. Preserved component research also contains classifiers and evaluation work; the existence of those artifacts does not mean a separate trained news classifier is invoked by the main Analyze route.

For the live term scorer:

\[
\text{sentiment score}=\frac{N_{positive}-N_{negative}}
{N_{positive}+N_{negative}},
\]

with score zero when no listed terms are found. Scores at or above 0.2 are positive; at or below -0.2 are negative; intermediate scores are neutral.

### Output and Contribution

It returns dated articles, sentiment counts, event tags, relevance scopes and coverage warnings. Its contribution is connecting relevant event evidence to the selected stock rather than displaying an unrelated generic feed.

### Boundaries

News retrieval cannot collect every possible article. Financial wording, negation, sarcasm and limited article text can affect sentiment accuracy. A relevant negative headline does not prove it caused a price fall.

Gold, oil, VIX, USD/LKR relationships and ASPI comparison belong to **Component 4's external-market context**, not Component 3's research ownership. Both adapters currently share `externalContextService.js`, but return separate outputs.

Implementation: `research/component3/` and `collectNewsSentiment` in `server/src/services/externalContextService.js`.

## 9. Component 4: Explainable External-Market Risk

### Purpose

Classify current financial-market risk as LOW, MEDIUM or HIGH and explain the measured factors behind the classification.

### Classifier Inputs

- Selected-stock price and trading activity.
- Shorter/longer moving references.
- Recent return, drawdown, variability and unusual volume.
- Gold, crude oil and VIX levels and changes.
- Stock identity where required by the preserved model.

### Wider Context

This contribution also collects ASPI and USD/LKR evidence and examines stock-specific daily-return relationships with external factors.

Gold, oil and VIX are classifier inputs. ASPI and USD/LKR supply wider interpretation; they should not be described as inputs to that preserved classifier when they are not.

Where there is enough overlapping data, the adapter estimates correlation and single-factor sensitivity and explains possible business exposure. For example, oil can affect fuel and distribution costs, but a diversified group's exposure may be mixed rather than uniformly negative.

These relationships describe association. A correlation or its square does not establish the percentage of a stock's movement caused by a factor.

### Risk Model and Explanations

The preserved CSE model uses a random forest and provides predicted-class SHAP explanations. It supports the original BIL and JKH scope.

Additional securities use a separate stock-specific fitting workflow when sufficient data and global factors exist. This uses the exact selected security, not a proxy company. Its own chronological evaluation and stock-only comparison are recorded before refitting.

The historical global inputs for these additional fits are aligned before the CSE session to reduce same-day overseas-close leakage.

### Outputs and Research Contribution

The stage returns the current risk category, supporting/opposing factor meanings, factor dates, business channels and availability warnings.

Its contribution is combining stock behaviour with global indicators and explaining the classification instead of showing an unexplained risk label.

### Boundaries

The target categories describe a research-defined **current risk state**. Classification accuracy measures agreement with that definition, not accurate prediction of future losses.

A stock can have a rising forecast path and HIGH current risk, or a stable path and LOW current risk. These are different questions, not automatically conflicting results.

SHAP explains the classifier's use of inputs; it does not establish causation or prove that a risk category is objectively correct.

Implementation: `research/component4/`, `server/src/services/riskImpactService.js` and `collectMarketRiskContext` in `server/src/services/externalContextService.js`.

## 10. How the Final Stock Summary Is Produced

The shared integration layer combines the structured evidence from all four contributions. It is not a fifth research component.

Inputs include:

- Price paths, uncertainty, deviations, anomalies and model cautions.
- Report-backed strengths and concerns.
- Dated news, sentiment and events.
- ASPI comparison, external-factor associations and explained risk.
- Missing evidence and source limitations.

The combined output explains:

1. The current stock picture.
2. Evidence working in the company's favour.
3. Risks or weaknesses that could offset that potential.
4. Whether measured movement appears stock-specific or shared with the market.
5. Conditions that might improve or weaken the outlook.
6. What could not be established reliably.

The main implementation is `component_2/src/fuse_insights.py`, invoked through `server/src/services/unifiedInsightService.js`.

### Model-Based Wording and Fallbacks

The application supports three explanation modes:

| Mode | Behaviour |
|---|---|
| Azure provider, explicitly enabled | Uses the configured Azure deployment for supported wording operations |
| Local Ollama provider | Uses a configured local model to rewrite selected evidence-based narratives |
| Disabled, unavailable or rejected generation | Retains the deterministic evidence-based explanation; provider failures or rejected wording can add fallback warnings |

The local adapter's default model identifier is `qwen2.5:3b-instruct-q4_K_M`. Its presence in code does not prove the model is installed or running.

Local rewording checks protected names and numbers and is restricted to selected narratives. Report findings also undergo evidence checks. The Azure integration checks the required response structure and retains deterministic core outlook/scenario fields rather than accepting model replacements for them. These checks differ across paths and do not guarantee semantic accuracy or complete factual verification.

Generated wording is not intended to recalculate forecast paths or add trading instructions. Rejected or unavailable generation retains the evidence-based fallback.

An English summary appearing on screen therefore does **not** prove that OpenAI or a local language model generated it. For the local wording path, inspect `outputs.report.generation` and `outputs.unifiedInsight.generation`, including available `mode` and `fallback_used` fields. Provenance metadata is not consistently populated across all Azure and disabled-provider paths; its absence is not proof of successful model generation.

For events such as conflict or disaster recovery, the summary should use conditional language. The system does not have a verified causal model establishing a specific price if a conflict ends.

## 11. Where the Data Comes From

| Evidence | Current source approach | Important distinction |
|---|---|---|
| Listed company/security identity | CSE A-Z company directory | Directory membership is not validated model coverage |
| Latest reported prices | Official CSE trade-summary request | Latest quotes can differ from the latest completed model session |
| Existing historical OHLCV | MongoDB records, including imported CSV history | Source basis and quality must be preserved |
| New/repair history | CSE daily records plus actual TradingView CSELK observations, subject to reconciliation | Older split-adjusted secondary history is not exchange-only verified history |
| Financial performance | User-uploaded quarterly/annual PDF | Extraction can miss information or encounter unreadable tables |
| News and sentiment | Relevant search/RSS article evidence | Coverage is incomplete and sentiment is not causal attribution |
| Gold, oil, VIX and FX context | Market-history provider requests and dated caches | Availability, timing and overlap must be checked |
| Broad-market comparison | CSE ASPI data and stock comparison | Shared direction is not proof of a single common cause |

The application uses source APIs/endpoints, RSS retrieval and historical-data adapters. It does not merely crawl every website or obtain the entire dataset from one API.

New history preparation can request up to 5,000 actual observations. Recent secondary-source high/low values are checked against official records before eligible observations are admitted. A missing opening price is not invented from the previous close.

Private snapshots and audit information support review of updates. Missing sessions and source disagreements remain disclosed.

## 12. Company Coverage and Eligibility

The current selector uses the CSE directory rather than a fixed two-company list. A saved audit recorded 302 listings; the directory size can change.

Every current listing can be selected for preparation. This is not a promise that all four stages can produce supported results for every listing.

The current full forecast workflow requires at least 1,000 valid observations. New-series preparation also checks recent positive-volume participation, recent source agreement and data freshness.

An illiquid, newly listed, suspended or unavailable security can lack enough evidence. The system should show that limitation rather than copy another stock's model or fabricate history.

Voting and non-voting share classes are separate securities. Their datasets and predictions must not be substituted for each other.

JKH and BIL remain the original preserved research cases. New stock-specific runs do not inherit those stocks' saved accuracy figures.

The server prepares history on demand. It does not pre-download and train every listed security whenever it starts.

## 13. What Is Recomputed and What Is Reused

| Item | Behaviour |
|---|---|
| Latest quote refresh | Requested as part of a new analysis |
| Stored history | Reused as source observations, checked/refreshed as available |
| Component 1 expected-price and horizon work | Fresh fitting/selection from the current accepted history snapshot |
| Uploaded financial report | Reprocessed for that run; the PDF remains the user's supplied source |
| Ten-prompt report benchmark | Offline research, not repeated on every click |
| News | Requested for the selected company and broader context |
| Original BIL/JKH risk artifact | Loaded for its supported scope rather than retrained every click |
| Additional-security risk model | Uses the separate stock-specific fitting workflow |
| Global-factor history | May be cached and refreshed according to staleness rules |
| Translation | Uses pretrained translation weights and validated text caching, not model retraining |
| Locked research forecasts | Preserved for validation, not substituted for live forecasts |

Fresh analysis means recomputation from the accepted inputs. If the data and deterministic configuration are unchanged, two runs can correctly return the same values.

## 14. English, Sinhala and Tamil

The interface supports English, Sinhala and Tamil. Navigation and form labels use local message dictionaries.

Dynamic output translation is a separate stage. With `TRANSLATION_PROVIDER=nllb`, it uses an offline NLLB-200 distilled 600M model through CTranslate2 with int8 weights.

Translation covers combined narratives, company strengths/concerns, risk explanations, recovery discussions and displayed news titles. It preserves identifiers and financial values rather than recomputing them.

Switching language:

- Does not train the forecasting models again.
- Does not change the original English evidence.
- Does not translate the uploaded PDF into a new report.
- Does not establish that the sentiment model understands Sinhala/Tamil source news.

Validated translations are cached in memory. Failed or rejected translations retain clearly labelled English with a notice.

Automated checks protect numbers, names and symbols, but do not establish translation accuracy or comprehension. Native-speaker review remains necessary. The bundled NLLB option has research/non-commercial licensing restrictions and is not a certified financial translator.

Implementation: `client/src/i18n/messages.js`, `server/src/services/translationService.js`, `component_2/src/local_translation.py` and `component_2/src/translate_insights.py`.

## 15. Database and File Storage

MongoDB is configured by `MONGODB_URI` in the backend environment. Credentials are not embedded in the frontend or reproduced here.

### Collections

| Collection | Purpose |
|---|---|
| `users` | User/admin identity, hashed passwords, roles and account activity |
| `stocks` | Historical prices, volume, company/security identity, dates and import/source information |
| `financialreports` | Upload metadata, ownership, selected stock and processing status |
| `analysisruns` | Temporary integrated outputs, warnings, status and expiry |
| `news` | A model used by separate news functionality; distinct from the main run's embedded news evidence |

MongoDB uses collections, not relational tables. The application has grown beyond the original two-collection plan.

### Files

- Uploaded PDFs are stored privately under the server's report-upload directory.
- Market training snapshots and integration inputs use temporary server-side files that are cleaned up by their adapters.
- Stock-preparation and risk workflows retain private audit/run evidence.
- Research packages retain notebooks, source, saved artifacts and evaluation files.
- Local model weights live outside the tracked application source.

Analysis records are assigned an expiry 24 hours after creation. MongoDB TTL cleanup is asynchronous; deletion need not happen at the exact second of expiry.

This TTL does **not** automatically delete uploaded PDFs, accounts, stock history or all private audit files. Their retention needs separate management.

## 16. Accounts, Administration and Security

### Users

Users can register, sign in, sign out and work with their own reports and analysis records. Report/result access is checked server-side, not only by hiding interface controls.

### Administrators

The admin sign-in route is `/observatory/secure-entry`. It is a separate entry, not a public user-login switch.

Admin functions include:

- Viewing users and account activity.
- Creating, editing and deleting permitted accounts.
- Assigning supported roles.
- Resetting passwords without viewing existing plaintext passwords.
- Importing historical price data by CSV.
- Reviewing and maintaining stored market records.
- Viewing workflow information useful for demonstrations.

The hidden URL is not the security boundary. Authentication and admin-role checks enforce access.

### Implemented Controls

- Hashed passwords.
- Signed session tokens with verification on protected requests.
- HTTP-only session cookies, same-site policy and production secure-cookie setting.
- Backend role and ownership checks.
- Input validation and request-size limits.
- Upload-type and file-size checks.
- Allowed-origin CORS configuration.
- Security headers and request-rate limiting.
- Server-side secret configuration.
- Private report storage rather than a public report-file route.
- Child-process timeouts, bounded queues and cleaned temporary inputs.

These controls are not a certification of production security. Public deployment still needs reviewed HTTPS/proxy settings, dependency maintenance, backups, upload hardening, operational monitoring and a full security assessment. Never publish environment files or reuse exposed credentials.

## 17. Main API and Source Map

| Function | Main location |
|---|---|
| Public interface and workspace | `client/src/pages/` |
| API application and middleware | `server/src/app.js` |
| Authentication | `server/src/controllers/authController.js` and `server/src/middleware/auth.js` |
| Analysis coordination | `server/src/controllers/analysisController.js` |
| Fresh market execution | `server/src/services/marketInsightService.js` |
| Company directory and history preparation | `server/src/services/companyDirectoryService.js` and `stockPreparationService.js` |
| Current quotes and history repair | `server/src/services/cseQuoteService.js` and `marketHistoryService.js` |
| Financial-report inspection and analysis | `server/src/services/reportValidationService.js` and `reportInsightService.js` |
| News and external-context adapters | `server/src/services/externalContextService.js` |
| Risk execution | `server/src/services/riskImpactService.js` |
| Final synthesis | `server/src/services/unifiedInsightService.js` and `component_2/src/fuse_insights.py` |
| Progress events | `server/src/services/analysisProgressService.js` and `research/component1/src/runtime_progress.py` |
| Dynamic translation | `server/src/services/translationService.js` |
| Database schemas | `server/src/models/` |

Important API groups are `/api/auth`, `/api/stocks`, `/api/reports`, `/api/analysis`, `/api/admin` and `/api/news`.

A user starts analysis with `POST /api/analysis`, follows `GET /api/analysis/progress/:requestId` and retrieves an owned result through `GET /api/analysis/:analysisId`. Translation is requested when retrieving the result with the chosen language.

## 18. Demonstrating All Four Contributions

1. Use an eligible stock and an appropriate recent report; JKH/BIL are the original research examples.
2. Show the exact security, historical row count and latest completed data date.
3. Upload the report and show company/period validation.
4. Start analysis with the backend terminal visible.
5. Show quote/history preparation and the four separate stage logs.
6. For Component 1, show fresh fitting events, run identity, expected/actual price, deviation, score, cutoff, anomaly decision and horizon ranges.
7. For Component 2, open the source PDF and locate the pages supporting displayed strengths and concerns.
8. For Component 3, show the dated source links, relevant event tags and sentiment classifications.
9. For Component 4, show factor dates, explained risk category and measured external relationships.
10. Show how the overall summary connects the evidence without erasing disagreement.
11. Inspect generation provenance to distinguish local/cloud model wording from a deterministic fallback.
12. Switch language and demonstrate that the same financial evidence is preserved.
13. Finish with baseline cautions, missing evidence and the non-advisory statement.

Notebooks and stored evaluation artifacts demonstrate training and research evidence. Backend logs demonstrate live orchestration. Neither one alone proves that the whole system has been evaluated with real investors.

## 19. Research Contribution and Validation Boundaries

| Contribution | Research focus | Evidence still requiring care |
|---|---|---|
| Component 1 | Participation-aware deviations, separate band checks, forecast uncertainty and explanation stability | Original forecast baseline failures, retrospective label leakage, rare-event counts and broader prospective evaluation |
| Component 2 | Grounded report extraction and comparison of prompt strategies | Heuristic expected outputs, complex PDF layouts and independent human-validated extraction tests |
| Component 3 | Relevant dated events and sentiment for the selected company/market | CSE-specific labelled relevance/sentiment tests and incomplete source coverage |
| Component 4 | Explained current-risk classification combining stock and global indicators | Label-definition validity, temporal robustness and distinguishing label fidelity from future-loss prediction |
| Shared integration | One understandable, traceable stock outlook | Human comprehension, usefulness, consistency and translation quality require separate evaluation |

The completed software demonstrates integration. It does not, by itself, prove all proposed novelties, financial usefulness, generalisation or user understanding.

A partial analysis can still contain useful evidence. However, a completed stage can also carry coverage or quality warnings. Completion status must be read together with those warnings, not as a guarantee that every input is reliable.

## 20. Running the Application

After installing the dependencies and configuring the private environment as described in `README.md`, run two terminals from the repository root:

```bash
# Terminal 1: backend
npm --prefix server run dev
```

```bash
# Terminal 2: frontend
npm --prefix client run dev -- --host 127.0.0.1
```

The usual local frontend is `http://127.0.0.1:5173` and backend port is 5001. The actual values follow the environment configuration. Keep browser/API hostnames consistent for session cookies.

MongoDB and the selected Python environment must be available. Local wording requires a running Ollama model if selected; offline translation requires its separately downloaded weights. The frontend alone cannot perform authentication or analysis.

## 21. The Separate Academic Website

The published academic website is an HTML/CSS research archive documenting the project and its contributions.

It is not the working MERN application. It does not perform live predictions, accept analysis reports or connect to the research database.

Its source is `output/academic-website-R26_IT_076/`. Hosting that static archive does not deploy the Express API, Python workflows, MongoDB or local models.

## 22. Final Summary

The complete system turns four different evidence streams into one understandable stock picture:

> Component 1 explains measured price behaviour and possible future ranges. Component 2 explains company performance from the uploaded report. Component 3 explains relevant reported events and sentiment. Component 4 explains current external-market risk. The integration layer connects these findings, preserves uncertainty and presents the result in the user's selected language.

Its purpose is to make evidence easier to understand, not to remove uncertainty from investing.
