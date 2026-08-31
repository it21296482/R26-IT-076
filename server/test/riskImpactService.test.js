const test = require("node:test");
const assert = require("node:assert/strict");

const {
  assessRiskImpact,
  buildRiskFeatures,
  sampleStandardDeviation,
} = require("../src/services/riskImpactService");

const rows = Array.from({ length: 51 }, (_, index) => ({
  symbol: "JKH.N0000",
  tradeDate: new Date(Date.UTC(2026, 7, 31 - index)),
  close: 20 - (index * 0.1),
  volume: 1_000_000 - index,
}));
const marketRiskContext = {
  externalFactors: {
    factors: [
      { key: "gold", latestValue: 3400, change30dPct: 3.2, latestDate: "2026-08-28" },
      { key: "oil", latestValue: 70, change30dPct: -4.1, latestDate: "2026-08-28" },
      { key: "vix", latestValue: 21, change30dPct: 8, latestDate: "2026-08-28" },
    ],
  },
};

test("calculates sample standard deviation consistently with the supplied component", () => {
  assert.ok(Math.abs(sampleStandardDeviation([1, 2, 3]) - 1) < 0.000001);
});

test("builds the live risk inputs from Component 4 external-market factors", () => {
  const features = buildRiskFeatures({ symbol: "JKH.N0000", rows, marketRiskContext });
  assert.equal(features.stock, "JKH");
  assert.equal(features.close, 20);
  assert.equal(features.gold, 3400);
  assert.equal(features.oil, 70);
  assert.equal(features.vix, 21);
  assert.equal(features.gold_change30d_pct, 3.2);
  assert.ok(Number.isFinite(features.return20_pct));
  assert.ok(Number.isFinite(features.drawdown20_pct));
  assert.ok(Number.isFinite(features.volatility_pct));
  assert.ok(Number.isFinite(features.volume_ratio20));
  assert.ok(Number.isFinite(features.ma10));
  assert.ok(Number.isFinite(features.ma50));
  assert.ok(Number.isFinite(features.volatility));
});

test("runs the risk adapter with the prepared evidence", async () => {
  let received = null;
  const StockModel = {
    find() {
      return { sort: () => ({ limit: () => ({ lean: async () => rows }) }) };
    },
  };
  const result = await assessRiskImpact(
    { symbol: "JKH.N0000", marketRiskContext },
    {
      StockModel,
      executeRisk: async (features) => {
        received = features;
        return { status: "completed", risk_level: "MEDIUM", top_drivers: [] };
      },
    }
  );

  assert.equal(received.stock, "JKH");
  assert.equal(result.risk_level, "MEDIUM");
});

test("does not invent a risk category for a stock outside the trained BIL and JKH scope", async () => {
  const StockModel = {
    find() {
      return { sort: () => ({ limit: () => ({ lean: async () => rows }) }) };
    },
  };
  await assert.rejects(() => assessRiskImpact(
    { symbol: "HHL.N0000", marketRiskContext },
    {
      StockModel,
      executeRisk: async () => ({
        status: "unavailable",
        code: "RISK_STOCK_NOT_SUPPORTED",
        message: "The evaluated CSE risk model was not trained for HHL.",
      }),
    }
  ), /not trained for HHL/);
});
