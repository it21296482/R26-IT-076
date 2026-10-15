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

## Current research-supported stocks

- John Keells Holdings PLC (`JKH.N0000`)
- Browns Investments PLC (`BIL.N0000`)

No third market artifact is claimed because a third locked forecast was not found in the supplied research workspace.

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
- set `RISK_ANALYSIS_TIMEOUT_MS` if the local Python risk adapter needs more than its default two-minute limit
- the reproducible CSE risk model supports BIL and JKH; its chronological test metrics and stock-only ablation are stored with the model artifact
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

The updated research implementation uses log-return learning, validation-selected
baseline blending, horizon-specific forecast selection, and past-only adaptive
anomaly cutoffs. Original deviation/volume formulas and locked forecasts remain
preserved. See `research/component1/MODEL_UPGRADE_REPORT.md` and the comparison
evidence in `research/component1/artifacts/upgrade_v2/`.

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

Choose **English**, **සිංහල**, or **தமிழ்** in the header. The choice is retained
across navigation and reloads. Navigation, account forms, analysis inputs, result
labels and admin controls use local translations, with no translation API needed.
Dates follow the selected language. Prices, ticker symbols, scores, model status
values, company names, CSV columns and original source quotes stay unchanged.

Generated report takeaways, the combined explanation, risk-driver descriptions,
and news headlines use the existing Azure explanation-service configuration
(`AZURE_OPENAI_*` and `PYTHON_BIN`). No separate public translation service receives
report summaries. This translation call requires valid Azure credentials even if
English analysis uses the local fallback. It may incur normal Azure usage charges.
Translations are cached in server memory for up to 30 minutes (maximum 2,000 strings)
and are not written over the original analysis. Switching language does not rerun
the research models. New analyses still refresh prices and run the original pipeline.

Automatic translations are labelled. A provider outage or changed numeric/ticker
content preserves the original English wording and shows an explicit translation
notice rather than hiding evidence. Research documentation and original source
documents remain in their original language; this does not add Sinhala/Tamil PDF
extraction or retrain the sentiment model. Native-speaker financial terminology
review is recommended before a public release.

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
