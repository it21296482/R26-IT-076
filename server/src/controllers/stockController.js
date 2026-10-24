const Stock = require("../models/Stock");
const { fetchTradeSummary, quotePriceList } = require("../services/cseQuoteService");
const { fetchCompanyDirectory, mergeCompanyUniverse } = require("../services/companyDirectoryService");
const { storedStockSummary, loadRiskCoverage, stockAvailability } = require("../services/stockCoverageService");

const getMarketPrices = async (req, res) => {
  try {
    const quotes = await fetchTradeSummary();
    return res.json({ stocks: quotePriceList(quotes), source: "Colombo Stock Exchange trade summary", fetchedAt: new Date().toISOString() });
  } catch {
    return res.status(503).json({ message: "CSE prices are temporarily unavailable. Try refreshing the price list." });
  }
};

const listStocks = async (req, res) => {
  const { symbol } = req.query;
  const filter = symbol ? { symbol: symbol.toUpperCase() } : {};

  const stocks = await Stock.find(filter).sort({ tradeDate: -1, createdAt: -1 }).limit(100);

  return res.status(200).json({ stocks });
};

const getStockUniverse = async (req, res) => {
  const [summary, coveredSymbols, directory] = await Promise.all([
    storedStockSummary(), loadRiskCoverage(), fetchCompanyDirectory().catch(() => null),
  ]);
  const stocks = mergeCompanyUniverse(directory?.companies || [], summary, coveredSymbols, stockAvailability);
  return res.status(200).json({ stocks, directory: directory && {
    source: directory.source, fetchedAt: directory.fetchedAt, complete: directory.complete,
  }, warning: !directory || !directory.complete ? "The company directory is temporarily incomplete. Available companies are still shown." : null });
};

module.exports = {
  listStocks,
  getStockUniverse,
  getMarketPrices,
};
