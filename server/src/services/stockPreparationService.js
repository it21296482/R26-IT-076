const { execFile } = require("child_process");
const { promisify } = require("util");
const fs = require("fs/promises");
const path = require("path");
const { createHash, randomUUID } = require("crypto");
const Stock = require("../models/Stock");
const { fetchCompanyDirectory } = require("./companyDirectoryService");
const { fetchOfficialHistory, refreshStockHistory } = require("./marketHistoryService");
const { tradeDateFromTimestamp } = require("./cseQuoteService");

const execute = promisify(execFile);
const SCRIPT = path.resolve(__dirname, "../../../research/component1/fetch_public_openings.py");
const AUDITS = path.resolve(__dirname, "../../uploads/stock-preparation");
const SOURCE = "cse-bootstrap:tradingview-split-adjusted";
const day = (value) => new Date(value).toISOString().slice(0, 10);
const validCandle = (row) => row && ["open", "high", "low", "close", "volume"].every((key) =>
  row[key] !== null && row[key] !== undefined && Number.isFinite(Number(row[key])))
  && ["open", "high", "low", "close"].every((key) => Number(row[key]) > 0)
  && Number(row.volume) >= 0 && Number(row.high) >= Math.max(row.open, row.close, row.low)
  && Number(row.low) <= Math.min(row.open, row.close, row.high);
const priceMatches = (a, b) => Number.isFinite(Number(a)) && b != null
  && Math.abs(Number(a) - Number(b)) <= Math.max(.011, Math.abs(Number(b)) * .0001);

const fetchLongHistory = async (symbol) => {
  let stdout;
  try {
    ({ stdout } = await execute(process.env.PYTHON_BIN || "python", [SCRIPT, "--symbol", symbol, "--bars", "5000"], {
      timeout: 50000, maxBuffer: 6 * 1024 * 1024,
    }));
  } catch {
    throw new Error("The public long-term history source did not provide usable daily data for this security.");
  }
  const result = JSON.parse(stdout);
  if (result.symbol !== symbol || !Array.isArray(result.rows)) throw new Error("Historical source returned a different security.");
  return result;
};

const requireListedCompany = async (symbol, loadDirectory = fetchCompanyDirectory) => {
  if (!/^[A-Z0-9]+\.[NX][0-9]{4}$/.test(symbol)) throw new Error("Select a valid CSE security.");
  const directory = await loadDirectory();
  const company = directory.companies.find((item) => item.symbol === symbol);
  if (!company) throw new Error("This security could not be confirmed in the current CSE directory. Please refresh and try again.");
  return company;
};

// Only actual observations are admitted. No calendar expansion, interpolation,
// prior-close openings, or copying a different share class's data is permitted.
const buildPreparationPlan = ({ company, history, official, today, createdBy }) => {
  if (history.symbol !== company.symbol || official.symbol !== company.symbol) throw new Error("Security identity mismatch.");
  const seen = new Set(), valid = [], rejectedDates = [];
  for (const observation of history.rows) {
    const date = observation.date;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date))) throw new Error("Invalid source date.");
    if (seen.has(date)) throw new Error("Duplicate source date.");
    seen.add(date);
    if (date >= today) continue;
    if (!validCandle(observation)) { rejectedDates.push(date); continue; }
    valid.push({ ...observation });
  }
  valid.sort((a, b) => a.date.localeCompare(b.date));
  const sourceMap = new Map(valid.map((row) => [row.date, row]));
  let compared = 0, matched = 0, officialReplacements = 0;
  const comparisons = [];
  const officialSeen = new Set();
  for (const observation of official.payload.chartData) {
    const date = tradeDateFromTimestamp(observation.t);
    if (!date) throw new Error("Invalid official history date.");
    const key = day(date);
    if (officialSeen.has(key)) throw new Error("Duplicate official history date.");
    officialSeen.add(key);
    if (key >= today) continue;
    const candle = sourceMap.get(key);
    if (!candle || !(observation.h > 0 && observation.l > 0)) continue;
    compared += 1;
    const agrees = priceMatches(candle.high, observation.h) && priceMatches(candle.low, observation.l);
    comparisons.push({ date: key, agrees });
    if (!agrees) continue;
    matched += 1;
    const reconciled = { ...candle, high: observation.h, low: observation.l, close: observation.p, volume: observation.q };
    if (validCandle(reconciled)) {
      Object.assign(candle, reconciled, { official: true });
      officialReplacements += 1;
    }
  }
  // Older bank prices can differ because the secondary series is split-adjusted.
  // Compare the CURRENT basis; retain older adjusted source observations unchanged
  // instead of forcing them to match older unadjusted exchange prices.
  const recent = comparisons.sort((a, b) => a.date.localeCompare(b.date)).slice(-20);
  const recentMatched = recent.filter((row) => row.agrees).length;
  if (recent.length < 10 || recentMatched / recent.length < .9 || !valid.at(-1)?.official) throw new Error(
    "The long-term history could not be reconciled with CSE daily high/low prices. A verified historical export is required.");
  const latest = valid.at(-1)?.date;
  if (!latest || Date.parse(today) - Date.parse(latest) > 10 * 86400000) throw new Error(
    "Recent completed trading history is unavailable for this security; no current forecast was invented.");
  const activeSessions = valid.slice(-252).filter((row) => Number(row.volume) > 0).length;
  const rows = valid.map((row) => ({ symbol: company.symbol, companyName: company.companyName,
    tradeDate: new Date(`${row.date}T00:00:00Z`), open: Number(row.open), high: Number(row.high),
    low: Number(row.low), close: Number(row.close), volume: Number(row.volume), adjustedClose: null, createdBy,
    source: row.official ? `${SOURCE}+official-hlcv` : SOURCE,
    notes: row.official
      ? "CSE closing price/high/low/total volume, with same-date matching TradingView opening. Older source observations are split-adjusted; no interpolation."
      : "Actual TradingView CSELK split-adjusted daily OHLCV. Older observations are not independently verified CSE totals. No interpolation." }));
  return { rows, quality: { validRows: rows.length, latestDate: latest, rejectedDates, compared, matched,
    agreement: matched / compared, officialReplacements, recentActiveSessions: activeSessions,
    recentCompared: recent.length, recentMatched, recentAgreement: recentMatched / recent.length,
    forecastReady: rows.length >= 1000 && activeSessions >= 80,
    sourceNote: "Older split-adjusted TradingView observations; recent CSE HLCV used only with matching daily high/low. Neither source guarantees complete corporate-action or crossing coverage." } };
};

// Bound both public-source requests and memory use; duplicate selections share
// preparation, but each analysis still fits its own model from the stored snapshot.
const pending = new Map();
let active = 0;
const waiting = [];
const withPreparationSlot = async (task) => {
  if (active >= 2) {
    if (waiting.length >= 8) throw new Error("Stock preparation is busy. Please try again shortly.");
    await new Promise((resolve) => waiting.push(resolve));
  } else active += 1;
  try { return await task(); } finally {
    const next = waiting.shift();
    if (next) next(); else active -= 1;
  }
};

const prepareStock = async ({ symbol, createdBy, company: suppliedCompany, apply = true }, {
  StockModel = Stock, fetchHistory = fetchLongHistory, fetchOfficial = fetchOfficialHistory,
  loadCompany = requireListedCompany, refreshHistory = refreshStockHistory, now = new Date(),
} = {}) => {
  symbol = String(symbol).toUpperCase();
  const company = suppliedCompany || await loadCompany(symbol);
  if (company.symbol !== symbol) throw new Error("Company identity mismatch.");
  const existing = await StockModel.find({ symbol }).sort({ tradeDate: 1 }).lean();
  // Preserve manually imported research history and its original source basis.
  if (existing.filter((row) => !String(row.source).startsWith("cse-")).length >= 1000) {
    const latest = day(existing.at(-1).tradeDate);
    if (now.getTime() - Date.parse(latest) > 10 * 86400000) {
      // An old CSV is not sufficient evidence of today's market state.
      const refresh = await refreshHistory(symbol, { StockModel });
      if (!refresh.through || now.getTime() - Date.parse(refresh.through) > 10 * 86400000) throw new Error("Recent stock history is unavailable.");
      return { symbol, mode: "existing_history", forecastReady: true, refresh };
    }
    let refresh;
    try { refresh = await refreshHistory(symbol, { StockModel }); }
    catch { refresh = { applied: false, warning: "Recent daily history could not be refreshed. The dated stored observations were used without inventing prices." }; }
    return { symbol, mode: "existing_history", forecastReady: true, refresh };
  }
  let history, official;
  try {
    history = await fetchHistory(symbol);
    official = await fetchOfficial(symbol, { security: { symbol, id: company.securityId } });
  } catch (error) {
    const stored = existing.filter(validCandle);
    const latest = stored.at(-1);
    const activeSessions = stored.slice(-252).filter((row) => Number(row.volume) > 0).length;
    if (stored.length >= 1000 && activeSessions >= 80 && String(latest?.source).startsWith(`${SOURCE}+official-hlcv`)
      && now.getTime() - new Date(latest.tradeDate).getTime() <= 10 * 86400000) {
      return { symbol, mode: "stored_sourced_history", forecastReady: true, validRows: stored.length,
        latestDate: day(latest.tradeDate), refresh: { applied: false,
          warning: "Live history could not be refreshed. A new model was fitted to the dated, previously checked history; no missing prices were invented." } };
    }
    throw error;
  }
  const plan = buildPreparationPlan({ company, history, official,
    today: day(tradeDateFromTimestamp(now.getTime())), createdBy });
  const result = { symbol, mode: "sourced_history", ...plan.quality, applied: apply };
  if (!apply) return result;
  if (!createdBy) throw new Error("An authenticated user is required to prepare stock history.");
  const existingMap = new Map(existing.map((row) => [day(row.tradeDate), row]));
  const changes = plan.rows.filter((row) => {
    const before = existingMap.get(day(row.tradeDate));
    if (!before) return true;
    if (!String(before.source).startsWith(SOURCE)) return false;
    return ["open", "high", "low", "close", "volume", "source", "companyName"].some((key) => before[key] !== row[key]);
  });
  const auditId = randomUUID();
  await fs.mkdir(AUDITS, { recursive: true, mode: 0o700 });
  await fs.writeFile(path.join(AUDITS, `${auditId}.json`), JSON.stringify({ result,
    capturedAt: now.toISOString(), sourceSha256: createHash("sha256").update(JSON.stringify({ history, official })).digest("hex"),
    sources: { history, official }, preimages: existing, rows: changes }), { mode: 0o600, flag: "wx" });
  if (changes.length) await StockModel.bulkWrite(changes.map((row) => {
    const before = existingMap.get(day(row.tradeDate));
    return { updateOne: before
      ? { filter: { _id: before._id, updatedAt: before.updatedAt }, update: { $set: { ...row, createdBy: before.createdBy } } }
      : { filter: { symbol, tradeDate: row.tradeDate }, update: { $setOnInsert: row }, upsert: true } };
  }), { ordered: true });
  return { ...result, auditId };
};

const ensureStockPrepared = (options, dependencies) => {
  const key = String(options.symbol).toUpperCase();
  if (pending.has(key)) return pending.get(key);
  const task = withPreparationSlot(() => prepareStock(options, dependencies)).finally(() => pending.delete(key));
  pending.set(key, task);
  return task;
};

module.exports = { buildPreparationPlan, prepareStock, ensureStockPrepared, requireListedCompany, fetchLongHistory, validCandle };
