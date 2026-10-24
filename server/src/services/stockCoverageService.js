const fs = require("fs/promises");
const path = require("path");
const Stock = require("../models/Stock");

const MINIMUM_HISTORY_ROWS = 1000;
const RISK_METADATA = path.resolve(__dirname, "../../../research/component4/models/cse_risk_model_metadata.json");

const validObservation = { $and: [
  ...["open", "high", "low", "close"].map((field) => ({ $gt: [`$${field}`, 0] })),
  { $gte: ["$volume", 0] },
  { $gte: ["$high", "$open"] }, { $gte: ["$high", "$close"] }, { $gte: ["$high", "$low"] },
  { $lte: ["$low", "$open"] }, { $lte: ["$low", "$close"] },
] };

const storedStockSummary = (StockModel = Stock, symbol) => StockModel.aggregate([
  ...(symbol ? [{ $match: { symbol } }] : []),
  { $sort: { tradeDate: -1, createdAt: -1 } },
  { $group: { _id: "$symbol", symbol: { $first: "$symbol" }, companyName: { $first: "$companyName" },
    latestClose: { $first: "$close" }, latestVolume: { $first: "$volume" }, latestTradeDate: { $first: "$tradeDate" },
    recordCount: { $sum: 1 }, validHistoryCount: { $sum: { $cond: [validObservation, 1, 0] } } } },
  { $sort: { companyName: 1 } },
]);

const loadRiskCoverage = async () => {
  try {
    const metadata = JSON.parse(await fs.readFile(RISK_METADATA, "utf8"));
    return new Set((metadata.supported_stocks || []).filter((code) => /^[A-Z0-9]+$/.test(code)).map((code) => `${code}.N0000`));
  } catch {
    // Fail closed if coverage cannot be established; never assume all stocks work.
    return new Set();
  }
};

const stockAvailability = (stock, coveredSymbols) => {
  const historyReady = Number(stock.validHistoryCount || 0) >= MINIMUM_HISTORY_ROWS;
  const modelCovered = coveredSymbols.has(stock.symbol);
  return { analysisAvailable: historyReady && modelCovered, historyReady, modelCovered,
    minimumHistoryRows: MINIMUM_HISTORY_ROWS,
    analysisStatus: historyReady && modelCovered ? "available" : historyReady ? "coverage_required"
      : modelCovered ? "history_required" : "history_and_coverage_required" };
};

const getStockAvailability = async (symbol, { StockModel = Stock, loadCoverage = loadRiskCoverage } = {}) => {
  const [summary, coverage] = await Promise.all([storedStockSummary(StockModel, symbol), loadCoverage()]);
  return stockAvailability(summary[0] || { symbol }, coverage);
};

module.exports = { MINIMUM_HISTORY_ROWS, storedStockSummary, loadRiskCoverage, stockAvailability, getStockAvailability };
