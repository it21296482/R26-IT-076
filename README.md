# AI Powered Stock Market Insight Generator for the Colombo Stock Exchange

This repository contains the current MERN base platform for the product experience around the project.

## Included

- `client/`: React + Vite frontend
- `server/`: Express + MongoDB backend
- `assets/`: source visuals
- `client/public/assets/`: web-ready copies of the visuals used by the UI

## Current product flow

- polished public landing page
- separate sign in and sign up pages for users
- hidden admin access route
- secure role-based sessions
- user workspace for:
  - understanding the product value
  - selecting a listed company using full name and ticker
  - uploading the latest annual report
  - preparing the insight workflow
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

## Environment notes

- backend env file: `server/.env`
- frontend env file: `client/.env`
- default backend port in the current local setup: `5001`

## Hidden admin entry

The public UI does not expose admin access. The current secret admin route is:

`/observatory/secure-entry`
