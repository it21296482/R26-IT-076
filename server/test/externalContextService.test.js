const test = require("node:test");
const assert = require("node:assert/strict");

const {
  analyzeSentiment,
  deduplicateNews,
  describeAssociation,
  eventTags,
  pearsonCorrelation,
  regressionSensitivity,
  buildFactorMeaning,
  classifyMarketComparison,
} = require("../src/services/externalContextService");

test("financial language receives a transparent sentiment label", () => {
  assert.equal(analyzeSentiment("Record profit and strong revenue growth").label, "positive");
  assert.equal(analyzeSentiment("Losses increased during a weak and volatile period").label, "negative");
  assert.equal(analyzeSentiment("The company published its report").label, "neutral");
});

test("market comparison distinguishes broad weakness from stock-specific decline", () => {
  const broad = classifyMarketComparison({ stockChangePct: -2.1, aspiChangePct: -0.8 });
  assert.equal(broad.classification, "broader_market_weakness");
  assert.match(broad.interpretation, /does not mean every listed stock declined/i);

  const specific = classifyMarketComparison({ stockChangePct: -2.1, aspiChangePct: 0.5 });
  assert.equal(specific.classification, "stock_specific_weakness");
  assert.match(specific.interpretation, /specific to this stock/i);
});

test("event categories include macro and geopolitical context", () => {
  const tags = eventTags("Oil prices increased as the regional war continued");
  assert.deepEqual(tags, ["commodities", "geopolitical"]);
});

test("duplicate headlines are removed", () => {
  const rows = deduplicateNews([
    { title: "CSE closes higher", publishedAt: "2026-08-20", url: "one" },
    { title: "CSE closes higher!", publishedAt: "2026-08-21", url: "two" },
  ]);
  assert.equal(rows.length, 1);
});

test("correlation calculation and wording avoid causal claims", () => {
  const correlation = pearsonCorrelation([[1, 2], [2, 4], [3, 6]]);
  assert.equal(correlation, 1);
  assert.match(describeAssociation(correlation), /correlation, not proof of cause/i);
});

test("factor sensitivity quantifies association without presenting it as cause", () => {
  const pairs = [[0.01, 0.02], [0.02, 0.04], [-0.01, -0.02], [0.005, 0.01]];
  const result = regressionSensitivity(pairs);
  assert.ok(Math.abs(result.beta - 0.5) < 0.0001);
  assert.ok(result.rSquared > 0.99);
  const meaning = buildFactorMeaning({
    symbol: "JKH.N0000",
    factor: { key: "oil", label: "Crude oil" },
    correlation: 0.5,
    beta: result.beta,
    change30dPct: 10,
  });
  assert.match(meaning.businessChannel, /fuel|energy|cost/i);
  assert.match(meaning.contributionEstimate, /not a causal attribution/i);
});
