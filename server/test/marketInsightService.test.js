const test = require("node:test");
const assert = require("node:assert/strict");

const { loadMarketInsight } = require("../src/services/marketInsightService");

test("loads a versioned market artifact for a supported stock", async () => {
  const insight = await loadMarketInsight("JKH.N0000");
  assert.equal(insight.symbol, "JKH.N0000");
  assert.equal(insight.horizons.length, 4);
  assert.equal(insight.horizons.at(-1).status, "not_validated");
});

test("does not fabricate an artifact for an unsupported stock", async () => {
  await assert.rejects(() => loadMarketInsight("UNKNOWN.N0000"), {
    code: "MARKET_ARTIFACT_UNAVAILABLE",
  });
});

