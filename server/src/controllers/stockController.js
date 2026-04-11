const Stock = require("../models/Stock");

const listStocks = async (req, res) => {
  const { symbol } = req.query;
  const filter = symbol ? { symbol: symbol.toUpperCase() } : {};

  const stocks = await Stock.find(filter).sort({ tradeDate: -1, createdAt: -1 }).limit(100);

  return res.status(200).json({ stocks });
};

const getStockUniverse = async (req, res) => {
  const summary = await Stock.aggregate([
    {
      $sort: {
        tradeDate: -1,
        createdAt: -1,
      },
    },
    {
      $group: {
        _id: "$symbol",
        symbol: { $first: "$symbol" },
        companyName: { $first: "$companyName" },
        latestClose: { $first: "$close" },
        latestVolume: { $first: "$volume" },
        latestTradeDate: { $first: "$tradeDate" },
        recordCount: { $sum: 1 },
      },
    },
    {
      $sort: {
        companyName: 1,
      },
    },
  ]);

  return res.status(200).json({ stocks: summary });
};

module.exports = {
  listStocks,
  getStockUniverse,
};
