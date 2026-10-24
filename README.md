# AI Powered Stock Market Insight Generator for the Colombo Stock Exchange

This repository contains the MERN application and reproducible research packages for the integrated project.

## Project overview

The system helps non-expert investors understand a selected Colombo Stock
Exchange company by bringing together its price behaviour, financial reports,
news, and wider-market risks. It presents one plain-language stock outlook,
including strengths, concerns, possible price paths, and uncertainty. It does
not give buying or selling instructions.

### Component 1: Market behaviour and anomaly detection

Studies historical stock prices and trading volume to learn the stock's usual
behaviour. It produces fresh forecast paths for approximately 4 trading days,
1 month, 3 months, and 6 months, with uncertainty ranges. It compares the actual
price with the expected price, calculates the deviation and a volume-adjusted
anomaly score, and checks whether the movement crosses a calibrated threshold.
Factor explanations help show what influenced the score.

**Contribution:** explains whether a price movement is unusual and shows possible
future paths without treating them as guaranteed targets.

Implementation and research: `research/component1/`.

### Component 2: Financial report understanding

Checks the company and reporting period of the uploaded quarterly or annual
report, extracts financial and operational information, and turns it into
understandable strengths and concerns. Findings retain page references and
source evidence. The research compares ten prompt strategies to identify a
suitable approach for explaining reports to beginner investors; benchmark
limitations remain documented rather than hidden.

**Contribution:** helps users understand company performance without having to
read and interpret the entire financial report themselves.

Implementation and research: `component_2/`.

### Component 3: Financial news and sentiment

Collects relevant company, local-market, and global financial news. It removes
duplicate articles, identifies important events, and assesses whether the news
expresses positive, negative, or neutral sentiment. Dated news evidence adds
context to the selected stock's recent movement; it does not prove that a
headline caused that movement.

**Contribution:** shows what is being reported about the company and market,
helping users understand the events and sentiment around a price change.

Research source and integration notes: `research/component3/`.

### Component 4: Explainable external-market risk

Combines stock behaviour with gold, crude oil, and VIX indicators to classify
current financial-market risk as LOW, MEDIUM, or HIGH. A Random Forest model
produces the classification, and SHAP identifies the factors that increased
or reduced it. Wider-context evidence also includes ASPI comparisons and
USD/LKR relationships where data is available. These are associations, not
proof of causation or predictions of investment returns.

**Contribution:** explains the stock's current risk reading and how broader
financial conditions relate to it, rather than showing an unexplained label.

Implementation and research: `research/component4/`.

### How the four components work together

The user signs in, selects a supported stock, uploads its latest financial
report, and clicks Analyze. The backend refreshes available market prices and
coordinates the four evidence workflows. The integration layer combines their
findings into one same-page explanation: what the company is doing well, where
risks exist, whether price behaviour is unusual, and what evidence could change
the outlook. Missing or unverified evidence is labelled rather than guessed.

Component 1 explains price behaviour; Component 2 explains company performance;
Component 3 explains news and sentiment; Component 4 explains external-market
risk. Their combined result supports understanding, while the investment
decision remains with the user. See
`research/INTEGRATED_SYSTEM_DEMONSTRATION.md` for backend demonstration details
and each contribution's evaluation limits.

## Academic website

Published archive: [R26-IT-076 Research Website](https://r26-it-076-research.netlify.app/).
Source: `output/academic-website-R26_IT_076/`.

This separate HTML/CSS website documents all four contributions, including
Component 2's prompt-comparison evidence. It is not the working stock-analysis
application and needs no database, backend, API keys, or build step.

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory output/academic-website-R26_IT_076
```

Open `http://127.0.0.1:4173`. Netlify uses a manual directory upload;
pushing to GitHub does not automatically redeploy this site.

## Included

- `client/`: React + Vite frontend
- `server/`: Express + MongoDB backend
- `assets/`: source visuals
- `client/public/assets/`: web-ready copies of the visuals used by the UI
- `research/component1/`: preserved market research, fresh on-demand runtime entry point, locked validation artifacts, and the executed forecast-validation notebook
- `component_2/`: financial-report research, prompt benchmark, verified runtime adapter, and tests
- `research/component3/`: preserved external-context research source and integration notes
- `research/component4/`: preserved explainable risk model, isolated runtime adapter, supporting dataset, integration notes, and tests
- `research/PROPOSAL_AND_IMPLEMENTATION_AUDIT.md`: requirements and evidence audit across all four proposals
- `research/INTEGRATED_SYSTEM_DEMONSTRATION.md`: exact backend flow, research novelty, viva script, and honest limitations

## Current product flow

- polished public landing page
- separate sign in and sign up pages for users
- hidden admin access route
- secure role-based sessions
- user workspace requiring a supported stock and its latest quarterly or annual PDF report
- report company and period verification both when the PDF is uploaded and immediately before analysis; stale or mismatched reports are rejected
- every Analyze click first refreshes current available-stock rows from the official CSE trade summary, then reruns the market workflow from the latest MongoDB history; locked forecasts are never used as live output
- market behavior, report understanding, news/sentiment, and external-market risk run as four explicit stages before their outputs are fused
- one same-page evidence-aware result containing forecast horizons, deviation/anomaly context, favourable and adverse price ranges, page-verified report strengths and concerns, dated news, stock-specific external-factor associations, explainable market risk, limitations, and a non-advisory statement
- short-lived analysis storage with automatic expiry after 24 hours
- admin console for:
  - viewing current users and account activity
  - resetting passwords
  - importing historical price data by CSV
  - reviewing recent market rows

## Data collections

### `users`

- stores user and admin accounts
- passwords are hashed and never displayed
- role-based access uses `admin` and `user`

### `stocks`

- stores historical price records
- each row includes company name, symbol, trade date, OHLC, adjusted close, volume, notes, and import source

### `financialreports`

- stores each user's uploaded PDF metadata and processing status
- uploaded files remain server-side and are never exposed through a public static route

### `analysisruns`

- stores integrated results and evidence warnings temporarily
- a MongoDB TTL index deletes each record after its `expiresAt` time

## Original Research Validation Stocks

- John Keells Holdings PLC (`JKH.N0000`)
- Browns Investments PLC (`BIL.N0000`)

These remain the original locked validation cases. Other current CSE directory
listings can now be selected for on-demand data preparation and stock-specific
training. This does not extend the original locked study's validation claims.

## Local run

### First-time setup

Use Node.js 22.12 or newer and Python 3.11 or newer, subject to the pinned
Python packages' platform support. A reachable MongoDB database is required.
The frontend alone cannot authenticate users or run analyses.

From the repository root:

```bash
npm ci
npm --prefix server ci
npm --prefix client ci
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r research/component1/requirements.txt
python -m pip install -r component_2/requirements.txt
python -m pip install -r research/component4/requirements.txt
cp server/.env.example server/.env
cp client/.env.example client/.env
```

On Windows, create the environment with `py -m venv .venv`, activate with
`.venv\Scripts\Activate.ps1`, and use `Copy-Item` instead of `cp`.

Edit the copied environment files before starting. Supply your MongoDB URI,
a strong random JWT secret, and your own admin seed password. Set `PYTHON_BIN`
to the absolute path of the virtual environment's Python executable. The admin
seed account is initialized during backend startup; example values are not
working credentials.

Use consistent hostnames: set `CLIENT_URL=http://127.0.0.1:5173` in
`server/.env` and `VITE_API_URL=http://127.0.0.1:5001/api` in `client/.env`.
For Atlas, configure the database user and permitted client IP address. The
database password is separate from the Atlas website login password.

### Backend

```bash
cd server
npm install
npm run dev
```

### Frontend

```bash
cd client
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`.

## Environment notes

- backend env file: `server/.env`
- frontend env file: `client/.env`
- default backend port in the current local setup: `5001`
- copy values from the two `.env.example` files and replace every placeholder
- set `PYTHON_BIN=python` (or the path to the project Python environment) and allow up to six minutes for a fresh market run
- report extraction and the combined explanation work locally from verified evidence by default (`USE_AZURE_OPENAI=false`)
- Azure wording enhancement is optional; enable it only with `USE_AZURE_OPENAI=true` and a valid rotated credential that matches the endpoint and deployment
- oil, gold, VIX, and USD/LKR relationships use overlapping one-year daily returns and are presented as associations with business context, never as proof of cause
- set `RISK_ANALYSIS_TIMEOUT_MS` if the local Python risk adapter needs more than its default three-minute limit
- the preserved CSE risk artifact supports BIL and JKH; other securities fit their own classifier and chronological comparison on demand, without modifying that artifact
- the admin console includes a plain-language four-stage workflow demonstration for research review
- never commit `.env` files or reuse credentials that have appeared in chat or Git history

## Verification

```bash
cd research/component1 && python -m pytest -q
cd component_2 && pytest -q
cd research/component4 && python -m pytest -q
cd server && npm test && npm audit --omit=dev
cd client && npm run lint && npm run build
```

The executed validation notebook is `research/component1/notebooks/component1_forecast_validation.ipynb`. Its documented result is that the locked May 2026 upward forecasts did not validate against the following three months, and a no-change baseline performed better for both available stocks.

## Component 1 model upgrade

Each live Analyze request trains the expected-price workflow and compares
Ridge regressions, Random Forest, Extra Trees, gradient boosting and an explicitly
labelled unchanged-price baseline separately for all four forecast horizons.
The lowest error on purged chronological validation selects the candidate; a
recent completed-outcome refit uses the current valid database history. A
persistence winner is labelled honestly, not disguised as a learned price move.
The original deviation/volume formula, past-only anomaly
thresholds, and locked validation forecasts are preserved. Live training needs
at least 1,000 valid observations for the purged four-horizon evaluation.

The UI receives actual stage/epoch events through an authenticated progress
stream and records a new run ID and input fingerprint. The searchable CSE quote
list covers every returned security. JKH and BIL retain the original research
artifacts; additional listings use the preparation workflow below. Before training,
a separate CSE daily-history check repairs
verified missing sessions and invalid/unfinished CSE snapshots. CSE supplies daily
closing prices, high/low and total share volumes. When CSE omits an opening,
TradingView's actual opening is accepted only for the same date with matching
high/low. Both sources and pre-change rows are saved privately for audit; nothing
is interpolated. Valid uploaded CSV records and locked research files are preserved.
Unresolved source gaps remain disclosed rather than hidden.

See `research/component1/README.md` for the current method and progress protocol.
`research/component1/MODEL_UPGRADE_REPORT.md` and
`research/component1/artifacts/upgrade_v2/` preserve the preceding v2 comparison,
not a claim that the new live regressions have prospective validation.

The integrated explanation distinguishes a fresh daily anomaly from a prolonged
shock that may already be reflected in recent trading. Conflict, disaster recovery,
business exposures and adverse conditions are discussed conditionally. Historical
price ranges are not relabelled as causal ceasefire or no-disaster price targets.
Company, market, global and disaster-recovery news receive balanced space rather
than allowing the first company feed to crowd out the remaining sources.

### Company Directory And Eligibility

See `research/CSE_COVERAGE_AND_TRAINING.md` for the dated 302-listing source audit,
additional-security runs and integrated regression results.

The stock selector reads CSE's A-Z company directory, cached for one hour to
avoid repeated upstream calls. It shows each company name and security code;
the latest-price table remains a separate CSE quote view. Percentage gains are
green, losses red, and zero/missing changes remain neutral.

Every listing in the current directory is selectable. The backend independently
confirms the exact security and canonical company name before accepting a report.
It validates the report before preparing history. Voting and non-voting shares
are separate securities; forecasts and risk models are never borrowed between them.

For a new selection, the server requests up to 5,000 actual split-adjusted daily
observations from TradingView CSELK and compares the latest 20 comparable sessions
with CSE high/low records. At least 10 comparisons, 90% recent agreement, and a
corroborated latest completed session are required. Older adjusted prices can
differ from unadjusted exchange records: they remain explicitly secondary-sourced,
not rescaled by an inferred adjustment. Where daily high/low agree, genuine CSE
closing prices and total volume take precedence. Missing openings, suspended
sessions, and failed requests are never filled with invented values.

Preparation is demand-driven, with two workers, a bounded queue, shared pending
requests, and insert-only new rows/version-checked updates. Identical rows are not
rewritten. Private source snapshots, checksums and preimages precede data changes.
The app does not download all 302 histories into a free Atlas database at startup.
Database storage and private audit retention still need monitoring as usage grows.

The full four-horizon workflow still requires 1,000 valid observations. New-series
preparation also requires at least 80 positive-volume observations among the last
252 and data no older than 10 calendar days. These are conservative operational
guards, not research-validated liquidity or accuracy thresholds. An illiquid,
recently listed, suspended or unavailable security can still produce report/news
evidence, but unsupported forecasts and risk readings are explicitly unavailable.
Selecting a stock is not a promise that sufficient evidence exists for every stage.

Additional securities train their own risk classifier using their own history,
Gold/Oil/VIX history and the existing current-risk index definition. Historical
global closes are aligned strictly before the CSE session. A chronological 80/20
check and stock-only ablation are recorded before refitting on completed outcomes;
the original BIL/JKH files are unchanged. These metrics assess agreement with
research-defined risk labels, not future-loss prediction or investment returns.

Audit actual source eligibility without database writes:

```bash
cd server
npm run audit:stock-coverage -- --all
```

The dated result is `output/cse-listing-history-audit.json`. It distinguishes data
eligibility from missing/stale/conflicting evidence; it is not 302 trained-model
accuracy validation. To verify one additional security's actual preparation,
fresh forecasts/anomalies and fresh risk fit against the configured database:

```bash
node scripts/verifyAdditionalStock.js COMB.X0000
```

That local verification writes genuine history using an existing administrator
as its import owner. It does not bypass report validation or claim to test a
financial report that has not been supplied for that company.

```bash
python -m pytest research/component1/tests -q
python research/component1/evaluate_model_upgrade.py --epochs 18
```

The evaluation command can take several minutes. Retrospective improvements
are not independent prospective validation, and no price outcome is guaranteed.

## Troubleshooting

- Connection refused on port 5001: check the backend terminal and database
  connection; the frontend does not start the API automatically.
- `querySrv ENOTFOUND`: check the MongoDB hostname and DNS. Replace the sample
  URI instead of leaving `your_cluster.mongodb.net` in the configuration.
- A 401 from `/api/auth/me` before login can be expected. Repeated 401s after
  login require checking consistent hostnames, cookies, and environment values,
  then signing in again.
- Python import errors: check that `PYTHON_BIN` uses the environment where the
  requirements were installed.
- Evidence warnings indicate missing or unverified inputs, not successful
  predictions. Do not substitute invented data.

## Security and limitations

Never commit `.env`, uploaded reports, private exports, or credentials. Rotate
credentials previously disclosed in chat or Git history. Admin security depends
on server-side authentication and role checks, not on hiding the sign-in URL.
Configure HTTPS and deployment security separately before exposing the MERN
application. The Netlify site hosts only the academic archive.

This project provides research evidence and explanations, not financial advice.

## Languages

### Temporary Local Explanation Mode

The local development configuration can use Ollama instead of Azure. Install and
start Ollama on the same computer, then pull a model if it is not already present:

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
```

Set `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`,
`OLLAMA_MODEL=qwen2.5:3b-instruct-q4_K_M`, `OLLAMA_NUM_CTX=8192` and
`USE_AZURE_OPENAI=false` in `server/.env`, then
restart the backend. No cloud key is used in this mode and the adapter only
accepts a loopback endpoint, with redirects and environment proxies disabled.

The report extractor still verifies statement rows and page quotes first. The
local model rewrites its verified summary without replacing the extracted
strengths, concerns or source quotes. The combined explanation rewrites the
headline, overall stock overview and company-report takeaway from the integrated
evidence. Forecasts, risk categories, source evidence and detailed conditional
scenario calculations remain unchanged. Names and financial values are protected;
changed markers, numbers, risk labels and explicit advice are rejected. These
checks are not a guarantee of semantic accuracy or a substitute for research
evaluation of the new provider.

Generation provenance is recorded in `outputs.report.generation` and
`outputs.unifiedInsight.generation`. Successful local wording uses
`mode=local_model`; rejected or unavailable wording uses
`mode=rule_based_fallback`, `fallback_used=true` and a visible warning. A completed
analysis alone does not prove that model wording was used. Local translations
use a separate translation-specific model, not the small English explanation
model, and retain the financial-value checks. Native-speaker review remains necessary.
Local generation may take longer and
needs sufficient memory alongside the forecasting workflow.

To restore Azure later, set `LLM_PROVIDER=azure`, `USE_AZURE_OPENAI=true`, provide
valid rotated Azure settings and restart. The preserved prompt benchmark and
its original evaluation do not establish the quality of this temporary local mode.

### Language Behaviour

Dynamic Sinhala/Tamil explanations use offline NLLB-200 (600M, int8) when
`TRANSLATION_PROVIDER=nllb`. This includes the combined summary, strengths,
risks, conditional recovery outlook, report explanations and news titles, not
just navigation headings. Long narratives are split without discarding their
remaining sentences; invalid translations retain clearly labelled English.
Translations never recalculate forecasts or modify the saved English evidence.

Install `component_2/requirements-translation.txt` in the backend's Python
environment. Download the CTranslate2 model once (about 630 MB; allow 1 GB free):

```bash
hf download JustFrederik/nllb-200-distilled-600M-ct2-int8 --revision 302d78f00e6fdb50a1064059df7c392b735e9d05 --include model.bin config.json sentencepiece.bpe.model shared_vocabulary.txt README.md --local-dir output/local-models/nllb-600m-int8
```

Run this command from the repository root. Set `TRANSLATION_PROVIDER=nllb` in
`server/.env` and restart the backend. `TRANSLATION_MODEL_DIR` may override the
default directory; otherwise leave it unset. Requests do not download weights or
send explanation text to a remote translation service. Model files remain in
the ignored output folder. The first language switch takes longer; validated
translations are cached in memory for 30 minutes.

**Research-only licence:** Meta's [NLLB model card](https://huggingface.co/facebook/nllb-200-distilled-600M)
specifies CC-BY-NC-4.0 and research limitations. This is not a certified financial
translator or licensed for commercial deployment. Preserve attribution and
obtain native-speaker review before using translations in financial decisions.
Do not present these automated checks as a measured translation-accuracy score.

Choose **English**, **සිංහල**, or **தமிழ்** in the header. The choice is retained
across navigation and reloads. Navigation, account forms, analysis inputs, result
labels and admin controls use local translations, with no translation API needed.
Dates follow the selected language. Prices, ticker symbols, scores, model status
values, company names, CSV columns and original source quotes stay unchanged.

For an explicitly configured cloud alternative, `TRANSLATION_PROVIDER=llm` uses
the selected explanation provider (`LLM_PROVIDER` and `PYTHON_BIN`). Azure requires
valid credentials and may incur normal Azure charges. The small local English
explanation model is not recommended for Sinhala/Tamil translation; use the
dedicated offline translator above instead.
Translations are cached in server memory for up to 30 minutes (maximum 2,000 strings)
and are not written over the original analysis. Switching language does not rerun
the research models. New analyses still refresh prices and run the original pipeline.

Automatic translations are labelled. A provider outage or changed numeric/ticker
content preserves the original English wording and shows an explicit translation
notice rather than hiding evidence. Research documentation and original source
documents remain in their original language; this does not add Sinhala/Tamil PDF
extraction or retrain the sentiment model. Native-speaker financial terminology
review is recommended before a public release.

Narrative translation covers the complete integrated summary, recovery discussion,
company strengths/concerns, uncertainty lists, factor explanations and displayed
news headlines. Small batches avoid oversized output failures; concurrent requests
queue instead of being silently skipped. Protected placeholders preserve company
names, currency/amount pairs, signs and figures, followed by a bilingual copy-edit
pass. These automated checks do not substitute for native-speaker review. A
rejected server credential is reported explicitly; local UI translations can work
while dynamic explanations remain unavailable until valid Azure settings are restored.

Language regression checks:

```bash
cd client
node --test tests/language.test.mjs
cd ../server
node --test test/translationService.test.js
```

## Hidden admin entry

The public UI does not link to admin access. The admin sign-in route is:

`/observatory/secure-entry`
