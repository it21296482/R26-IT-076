const test = require("node:test");
const assert = require("node:assert/strict");

const fs = require("fs/promises");

const { executeFreshAnalysis, historyCsv, loadMarketInsight, stockCodeFromSymbol } = require("../src/services/marketInsightService");

test("voting and non-voting identifiers cannot collapse to one forecast", () => {
  assert.equal(stockCodeFromSymbol("COMB.N0000"), "COMB");
  assert.equal(stockCodeFromSymbol("COMB.X0000"), "COMB.X0000");
});

const rows = Array.from({ length: 1000 }, (_, index) => ({
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
      horizons: [{ key: "6m", status: "available_with_caution", estimated_close_lkr: 22.5 }],
    }));
  };
  let refreshed = false;
  const insight = await loadMarketInsight("JKH.N0000", { StockModel, executeAnalysis,
    refreshHistory: async (symbol) => { assert.equal(symbol, "JKH.N0000"); refreshed = true; return { inserted: 2 }; } });
  assert.ok(refreshed);
  assert.equal(insight.history_refresh.inserted, 2);
  assert.equal(insight.symbol, "JKH.N0000");
  assert.equal(insight.run_mode, "fresh_on_demand");
  assert.equal(insight.horizons.at(-1).estimated_close_lkr, 22.5);
});

test("does not fabricate a forecast when history is insufficient", async () => {
  const EmptyStockModel = {
    find() {
      return { sort: () => ({ lean: async () => [] }) };
    },
  };
  await assert.rejects(() => loadMarketInsight("UNKNOWN.N0000", { StockModel: EmptyStockModel, refreshHistory: async () => ({}) }), {
    code: "MARKET_HISTORY_INSUFFICIENT",
  });
});

test("serializes history as a safe CSV", () => {
  const csv = historyCsv([{ ...rows[0], source: 'upload, "verified"' }]);
  assert.match(csv, /"upload, ""verified"""/);
});

test("failed Python execution has a safe public error and a backend diagnostic", async () => {
  const previous = process.env.PYTHON_BIN;
  const log = console.error;
  const diagnostics = [];
  try {
    process.env.PYTHON_BIN = "/nonexistent/cse-test-python";
    console.error = (...args) => diagnostics.push(args);
    await assert.rejects(() => executeFreshAnalysis({
      inputPath: "/tmp/history.csv", outputPath: "/tmp/output.json", stockCode: "JKH",
    }), (error) => {
      assert.equal(error.code, "MARKET_ANALYSIS_FAILED");
      assert.equal(error.cause.code, "ENOENT");
      assert.doesNotMatch(error.message, /\/nonexistent|Traceback|Command failed/);
      return true;
    });
    assert.equal(diagnostics.length, 1);
    assert.match(diagnostics[0][0], /market:JKH/);
  } finally {
    if (previous === undefined) delete process.env.PYTHON_BIN;
    else process.env.PYTHON_BIN = previous;
    console.error = log;
  }
});
