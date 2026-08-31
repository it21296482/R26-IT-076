const Stock = require("../models/Stock");

const CSE_TRADE_SUMMARY_URL = "https://www.cse.lk/api/tradeSummary";

const fetchTradeSummary = async ({ timeoutMs = 15000 } = {}) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(CSE_TRADE_SUMMARY_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "CSE-Insight-Research/1.0",
      },
      body: "",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`The CSE trade-summary source returned HTTP ${response.status}.`);
    }
    const payload = await response.json();
    if (!Array.isArray(payload.reqTradeSummery)) {
      throw new Error("The CSE trade-summary source returned an unexpected response.");
    }
    return payload.reqTradeSummery;
  } finally {
    clearTimeout(timeout);
  }
};

const tradeDateFromTimestamp = (value) => {
  const date = new Date(Number(value));
  if (Number.isNaN(date.getTime())) return null;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Colombo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return new Date(`${values.year}-${values.month}-${values.day}T00:00:00.000Z`);
};

const displayCompanyName = (value) => String(value || "")
  .toLowerCase()
  .replace(/\b\w/g, (character) => character.toUpperCase())
  .replace(/\bPlc\b/g, "PLC");

const quoteToStockRow = (quote, latest) => {
  const tradeDate = tradeDateFromTimestamp(quote.lastTradedTime);
  const close = Number(quote.closingPrice ?? quote.price);
  const open = Number(quote.open ?? close);
  const reportedHigh = Number(quote.high ?? close);
  const reportedLow = Number(quote.low ?? close);
  const volume = Number(quote.sharevolume ?? 0);
  if (!tradeDate || ![close, open, reportedHigh, reportedLow, volume].every(Number.isFinite)) {
    return null;
  }
  return {
    symbol: latest.symbol,
    companyName: displayCompanyName(quote.name || latest.companyName),
    tradeDate,
    open,
    high: Math.max(open, reportedHigh, reportedLow, close),
    low: Math.min(open, reportedHigh, reportedLow, close),
    close,
    adjustedClose: close,
    volume: Math.max(0, volume),
    source: "cse-live-trade-summary",
    notes: "Automatically refreshed from the official CSE trade summary when analysis started.",
    createdBy: latest.createdBy,
  };
};

const refreshAvailableStockQuotes = async (
  { StockModel = Stock, fetchQuotes = fetchTradeSummary } = {}
) => {
  const [latestRows, quotes] = await Promise.all([
    StockModel.aggregate([
      { $sort: { tradeDate: -1, createdAt: -1 } },
      {
        $group: {
          _id: "$symbol",
          symbol: { $first: "$symbol" },
          companyName: { $first: "$companyName" },
          tradeDate: { $first: "$tradeDate" },
          createdBy: { $first: "$createdBy" },
        },
      },
    ]),
    fetchQuotes(),
  ]);
  const quoteMap = new Map(quotes.map((quote) => [String(quote.symbol || "").toUpperCase(), quote]));
  const operations = [];
  const updatedSymbols = [];
  const skippedSymbols = [];

  for (const latest of latestRows) {
    const quote = quoteMap.get(String(latest.symbol).toUpperCase());
    const row = quote ? quoteToStockRow(quote, latest) : null;
    if (!row || row.tradeDate < new Date(latest.tradeDate)) {
      skippedSymbols.push(latest.symbol);
      continue;
    }
    operations.push({
      updateOne: {
        filter: { symbol: row.symbol, tradeDate: row.tradeDate },
        update: { $set: row },
        upsert: true,
      },
    });
    updatedSymbols.push(row.symbol);
  }

  if (operations.length) await StockModel.bulkWrite(operations, { ordered: false });
  return {
    source: "Colombo Stock Exchange trade summary",
    refreshedAt: new Date().toISOString(),
    updatedSymbols,
    skippedSymbols,
  };
};

module.exports = {
  fetchTradeSummary,
  quoteToStockRow,
  refreshAvailableStockQuotes,
  tradeDateFromTimestamp,
};
