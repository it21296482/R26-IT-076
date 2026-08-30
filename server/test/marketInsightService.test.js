const test = require("node:test");
const assert = require("node:assert/strict");

const fs = require("fs/promises");

const { historyCsv, loadMarketInsight } = require("../src/services/marketInsightService");

const rows = Array.from({ length: 300 }, (_, index) => ({
  symbol: "JKH.N0000",
  tradeDate: new Date(Date.UTC(2025, 0, index + 1)),
  open: 20 + index / 100,
  high: 21 + index / 100,
  low: 19 + index / 100,
  close: 20.5 + index / 100,
  volume: 100_000 + index,
  source: "test",
}));

const StockModel = {
  find() {
    return {
      sort() {
        return { lean: async () => rows };
      },
    };
  },
};

test("runs a fresh market analysis from current database history", async () => {
  const executeAnalysis = async ({ inputPath, outputPath }) => {
    const input = await fs.readFile(inputPath, "utf8");
    assert.match(input, /^date,symbol,open,high,low,close,volume,source/m);
    await fs.writeFile(outputPath, JSON.stringify({
      symbol: "JKH.N0000",
      run_mode: "fresh_on_demand",
      run_id: "test-run",
      horizons: [{ key: "6m", status: "not_validated" }],
    }));
  };
  const insight = await loadMarketInsight("JKH.N0000", { StockModel, executeAnalysis });
  assert.equal(insight.symbol, "JKH.N0000");
  assert.equal(insight.run_mode, "fresh_on_demand");
  assert.equal(insight.horizons.at(-1).status, "not_validated");
});

test("does not fabricate a forecast when history is insufficient", async () => {
  const EmptyStockModel = {
    find() {
      return { sort: () => ({ lean: async () => [] }) };
    },
  };
  await assert.rejects(() => loadMarketInsight("UNKNOWN.N0000", { StockModel: EmptyStockModel }), {
    code: "MARKET_HISTORY_INSUFFICIENT",
  });
});

test("serializes history as a safe CSV", () => {
  const csv = historyCsv([{ ...rows[0], source: 'upload, "verified"' }]);
  assert.match(csv, /"upload, ""verified"""/);
});
