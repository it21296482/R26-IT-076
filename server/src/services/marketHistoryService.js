const { execFile } = require("child_process");
const { promisify } = require("util");
const fs = require("fs/promises");
const path = require("path");
const { createHash, randomUUID } = require("crypto");
const Stock = require("../models/Stock");
const { fetchTradeSummary, tradeDateFromTimestamp } = require("./cseQuoteService");
const { fetchCompanyDirectory } = require("./companyDirectoryService");

const execute = promisify(execFile);
const CHART_URL = "https://www.cse.lk/api/companyChartDataByStock";
const OPENINGS_SCRIPT = path.resolve(__dirname, "../../../research/component1/fetch_public_openings.py");
const AUDIT_DIRECTORY = path.resolve(__dirname, "../../uploads/history-backfills");
const priceFields = ["open", "high", "low", "close", "volume"];
const dayKey = (value) => new Date(value).toISOString().slice(0, 10);
const finite = (value) => value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
const equal = (a, b) => Math.abs(Number(a) - Number(b)) < 1e-7;
const validRow = (row) => row && priceFields.every((key) => finite(row[key]))
  && ["open", "high", "low", "close"].every((key) => Number(row[key]) > 0)
  && Number.isSafeInteger(Number(row.volume)) && Number(row.volume) >= 0
  && Number(row.high) >= Math.max(Number(row.open), Number(row.close), Number(row.low))
  && Number(row.low) <= Math.min(Number(row.open), Number(row.close), Number(row.high));

const fetchOfficialHistory = async (symbol, { security: identifiedSecurity } = {}) => {
  const quotes = identifiedSecurity ? [] : await fetchTradeSummary();
  let security = identifiedSecurity || quotes.find((quote) => quote.symbol === symbol);
  if (security && security.symbol !== symbol) throw new Error("Official history security mismatch.");
  if (!security) {
    const directory = await fetchCompanyDirectory();
    const company = directory.companies.find((item) => item.symbol === symbol);
    if (company) security = { symbol, id: company.securityId };
  }
  if (!security || !Number.isInteger(security.id)) throw new Error("CSE did not identify this security.");
  const response = await fetch(CHART_URL, {
    method: "POST", body: new URLSearchParams({ stockId: String(security.id), period: "5" }),
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) throw new Error(`CSE daily history returned HTTP ${response.status}.`);
  const payload = await response.json();
  if (payload.id !== security.id || !Array.isArray(payload.chartData) || !payload.chartData.length
      || payload.chartData.some((row) => row.id !== security.id)) {
    throw new Error("CSE daily history did not match the selected security.");
  }
  return { symbol, source: CHART_URL, securityId: security.id, payload };
};

const fetchPublicOpenings = async (symbol) => {
  const { stdout } = await execute(process.env.PYTHON_BIN || "python", [OPENINGS_SCRIPT, "--symbol", symbol], {
    timeout: 50000, maxBuffer: 2 * 1024 * 1024,
  });
  const payload = JSON.parse(stdout);
  if (payload.symbol !== symbol || !Array.isArray(payload.rows)) throw new Error("Opening-price history did not match the selected security.");
  return payload;
};

// Plan first. A missing opening is never replaced with yesterday's close.
const planHistoryBackfill = ({ symbol, existing, official, openings = [], from, today }) => {
  const stored = new Map(existing.map((row) => [dayKey(row.tradeDate), row]));
  const openingMap = new Map();
  for (const row of openings) {
    if (openingMap.has(row.date)) throw new Error("Duplicate dates in opening-price history.");
    openingMap.set(row.date, row);
  }
  const template = existing.at(-1);
  if (!template) throw new Error("Stored company history is required before backfill.");
  const changes = [], unresolved = [], conflicts = [], observedDates = [];
  const seen = new Set();
  for (const observation of official) {
    const date = tradeDateFromTimestamp(observation.t);
    if (!date) throw new Error("CSE returned an invalid historical date.");
    const key = dayKey(date);
    if (seen.has(key)) throw new Error("Duplicate dates in CSE daily history.");
    seen.add(key);
    // Current-day snapshots are not a completed historical session.
    if (key < from || key >= today) continue;
    observedDates.push(key);
    const before = stored.get(key);
    const values = { high: observation.h, low: observation.l, close: observation.p, volume: observation.q };
    const same = before && Object.entries(values).every(([field, value]) => finite(value) && equal(before[field], value));
    if (validRow(before) && same) continue;
    if (validRow(before) && !String(before.source).startsWith("cse-")) {
      conflicts.push(key);
      continue;
    }
    const secondary = openingMap.get(key);
    const corroborated = secondary && validRow(secondary)
      && equal(secondary.high, values.high) && equal(secondary.low, values.low);
    const officialOpening = finite(observation.o) && Number(observation.o) > 0 ? Number(observation.o) : null;
    const priorOpening = before && finite(before.open) && Number(before.open) > 0
      && String(before.source).startsWith("cse-") ? Number(before.open) : null;
    const open = officialOpening ?? priorOpening ?? (corroborated ? Number(secondary.open) : null);
    const usesSecondary = officialOpening === null && priorOpening === null;
    const row = { symbol, companyName: template.companyName, tradeDate: date,
      open, ...values, adjustedClose: null, createdBy: before?.createdBy || template.createdBy,
      source: usesSecondary ? "cse-chart-history+tradingview-open" : "cse-chart-history",
      notes: usesSecondary
        ? "CSE daily closing price, high, low and total share volume; opening from TradingView CSELK on the same date with matching high/low. No interpolation."
        : "CSE daily closing price, high, low and total share volume; opening from CSE history or preserved CSE snapshot. No interpolation." };
    if (!validRow(row)) {
      unresolved.push(key);
      continue;
    }
    changes.push({ date: key, reason: !before ? "missing_session" : validRow(before) ? "finalized_cse_snapshot" : "invalid_session", before: before || null, row });
  }
  return { symbol, from, observedDates: observedDates.sort(), changes, unresolved: unresolved.sort(), preservedConflicts: conflicts.sort() };
};

const saveAudit = async (record) => {
  await fs.mkdir(AUDIT_DIRECTORY, { recursive: true, mode: 0o700 });
  const auditPath = path.join(AUDIT_DIRECTORY, `${record.id}.json`);
  await fs.writeFile(auditPath, JSON.stringify(record, null, 2), { flag: "wx", mode: 0o600 });
  return auditPath;
};

const refreshStockHistory = async (symbol, { StockModel = Stock, fetchOfficial = fetchOfficialHistory,
  fetchOpenings = fetchPublicOpenings, writeAudit = saveAudit, apply = true, from,
  now = new Date() } = {}) => {
  symbol = String(symbol).toUpperCase();
  if (!/^[A-Z0-9]+\.[NX][0-9]{4}$/.test(symbol)) throw new Error("Invalid CSE security symbol.");
  const existing = await StockModel.find({ symbol }).sort({ tradeDate: 1 }).lean();
  if (!existing.length) throw new Error("There is no stored company history to backfill.");
  const today = dayKey(tradeDateFromTimestamp(now.getTime()));
  // Start after the last uploaded history, not at a made-up weekday calendar.
  const lastImport = existing.filter((row) => !String(row.source).startsWith("cse-")).at(-1);
  const cutoff = new Date(now.getTime() - 350 * 86400000).toISOString().slice(0, 10);
  const start = from || (lastImport ? dayKey(new Date(new Date(lastImport.tradeDate).getTime() + 86400000))
    : new Date(now.getTime() - 90 * 86400000).toISOString().slice(0, 10));
  if (!/^\d{4}-\d{2}-\d{2}$/.test(start) || !Number.isFinite(Date.parse(start))) throw new Error("Invalid history start date.");
  const official = await fetchOfficial(symbol);
  if (official.symbol !== symbol) throw new Error("Official history belongs to a different stock.");
  const options = { symbol, existing, official: official.payload.chartData, from: start > cutoff ? start : cutoff, today };
  let plan = planHistoryBackfill(options);
  let openings = null, openingWarning = null;
  if (plan.unresolved.length) {
    try {
      openings = await fetchOpenings(symbol);
      if (openings.symbol !== symbol) throw new Error("Opening history belongs to a different stock.");
      plan = planHistoryBackfill({ ...options, openings: openings.rows });
    } catch (error) {
      openingWarning = "Some sessions still need a corroborated opening price; no replacement was invented.";
      console.warn(`[history:${symbol}] opening source unavailable: ${error.message}`);
    }
  }
  const id = randomUUID();
  const result = { id, symbol, applied: apply, source: "CSE daily chart; corroborated TradingView openings where necessary",
    from: plan.from, through: plan.observedDates.at(-1) || null, sourceSessions: plan.observedDates.length,
    inserted: plan.changes.filter((change) => change.reason === "missing_session").length,
    repaired: plan.changes.filter((change) => change.reason === "invalid_session").length,
    finalized: plan.changes.filter((change) => change.reason === "finalized_cse_snapshot").length,
    unresolvedDates: plan.unresolved, preservedConflicts: plan.preservedConflicts, warning: openingWarning };
  if (!plan.changes.length) return result;
  const capturedAt = now.toISOString();
  const sources = { official, openings };
  const sourceSha256 = createHash("sha256").update(JSON.stringify(sources)).digest("hex");
  // Durable source evidence and pre-images must exist before changing MongoDB.
  const auditPath = await writeAudit({ id, capturedAt, result, sourceSha256, sources, changes: plan.changes });
  if (apply) {
    const operations = plan.changes.map(({ before, row }) => ({ updateOne: before ? {
      filter: { _id: before._id, updatedAt: before.updatedAt },
      update: { $set: row }, upsert: false,
    } : {
      filter: { symbol, tradeDate: row.tradeDate }, update: { $setOnInsert: row }, upsert: true,
    } }));
    const written = await StockModel.bulkWrite(operations, { ordered: true });
    result.written = { inserted: written.upsertedCount, updated: written.modifiedCount };
  }
  result.auditFile = path.basename(auditPath);
  console.info(`[history:${symbol}] ${apply ? "applied" : "planned"}: ${result.inserted} missing, ${result.repaired} invalid, ${result.finalized} finalized, ${result.unresolvedDates.length} unresolved`);
  return result;
};

module.exports = { fetchOfficialHistory, fetchPublicOpenings, planHistoryBackfill, refreshStockHistory, validRow };
