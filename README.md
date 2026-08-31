# AI Powered Stock Market Insight Generator for the Colombo Stock Exchange

This repository contains the MERN application and reproducible research packages for the integrated project.

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

## Hidden admin entry

The public UI does not expose admin access. The current secret admin route is:

`/observatory/secure-entry`
