const test = require("node:test");
const assert = require("node:assert/strict");
const { translateAnalysis, validTranslation } = require("../src/services/translationService");

const fixture = () => ({
  _id: "analysis-123", user: "private-user-id", companyName: "John Keells Holdings PLC",
  stockSymbol: "JKH.N0000", status: "completed", createdAt: "2026-10-08T12:00:00Z",
  outputs: {
    market: {
      current_price_lkr: 19.80,
      horizons: [{ key: "6m", label: "6 months", status: "available", estimated_close_lkr: 24.00 }],
      anomaly: { detected: true, threshold: 0.446011, explanation: "Price is below expectation." },
    },
    report: { status: "completed", insight: {
      investor_friendly_insight: { summary: "Revenue increased 45%.", key_strengths: ["Cash generation improved."], key_concerns: ["Debt is high."] },
      evidence: [{ page: 4, source_quote: "Original audited financial quote." }],
    } },
    unifiedInsight: { status: "completed", insight: {
      headline: "JKH.N0000 has risks.", plain_language_overview: "The current price is LKR 19.80.",
      price_scenarios: { central_path_lkr: 24, narrative: "The 80% range is not guaranteed." },
      decision_balance: { supporting_evidence: ["Revenue increased 45%."], risk_evidence: ["Debt is high."] },
      non_advisory_note: "Not buying or selling advice.",
    } },
    riskImpact: { status: "completed", risk_level: "HIGH", confidence: 0.82, plain_explanation: "Risk is high.", top_drivers: [{ key: "VIX", label: "Global uncertainty", meaning: "Uncertainty increased." }] },
    newsSentiment: { status: "completed", articles: [{ title: "Investor confidence falls.", source: "News outlet", url: "https://example.com/news", publishedAt: "2026-10-08", sentiment: { label: "negative", score: -0.3 } }] },
  },
  warnings: ["A source was unavailable."],
});

test("English and unsupported language requests do not call the translation service", async () => {
  const original = fixture();
  const options = { translateBatch: () => assert.fail("Translation must not run") };
  assert.equal(await translateAnalysis(original, "en", options), original);
  assert.equal(await translateAnalysis(original, "invalid", options), original);
});

test("Sinhala changes only presentation strings; all four stages keep their evidence and enums", async () => {
  const original = fixture();
  const snapshot = JSON.stringify(original);
  let sent;
  const translated = await translateAnalysis(original, "si", {
    translateBatch: async (texts, language) => {
      sent = texts;
      assert.equal(language, "si");
      return Object.fromEntries(texts.map((text, i) => [String(i), `සිංහල ${text}`]));
    },
  });
  assert.equal(JSON.stringify(original), snapshot);
  assert.equal(translated.status, "completed");
  assert.equal(translated.stockSymbol, "JKH.N0000");
  assert.equal(translated.companyName, original.companyName);
  assert.equal(translated.createdAt, original.createdAt);
  assert.equal(translated.outputs.report.status, "completed");
  assert.deepEqual(translated.outputs.report.insight.evidence, original.outputs.report.insight.evidence);
  assert.equal(translated.outputs.market.horizons[0].key, "6m");
  assert.equal(translated.outputs.market.horizons[0].estimated_close_lkr, 24);
  assert.equal(translated.outputs.market.anomaly.threshold, 0.446011);
  assert.equal(translated.outputs.riskImpact.risk_level, "HIGH");
  assert.equal(translated.outputs.newsSentiment.articles[0].url, original.outputs.newsSentiment.articles[0].url);
  assert.deepEqual(translated.outputs.newsSentiment.articles[0].sentiment, original.outputs.newsSentiment.articles[0].sentiment);
  assert.ok(!sent.includes("Original audited financial quote."));
  assert.ok(!sent.includes("private-user-id"));
  assert.match(translated.outputs.report.insight.investor_friendly_insight.key_strengths[0], /සිංහල/);
  assert.match(translated.outputs.unifiedInsight.insight.headline, /සිංහල/);
  assert.equal(translated.localization.status, "completed");
});

test("Tamil supports report lists and preserves the non-advisory note", async () => {
  const translated = await translateAnalysis(fixture(), "ta", {
    translateBatch: async (texts) => Object.fromEntries(texts.map((text, i) => [String(i), `தமிழ் ${text}`])),
  });
  assert.match(translated.outputs.report.insight.investor_friendly_insight.key_concerns[0], /தமிழ்/);
  assert.match(translated.outputs.unifiedInsight.insight.non_advisory_note, /தமிழ்/);
  assert.equal(translated.localization.status, "completed");
});

test("provider failures retain original evidence and explicitly report unavailable translation", async () => {
  const original = fixture();
  const translated = await translateAnalysis(original, "si", {
    now: Date.now() + 3600000,
    translateBatch: async () => { throw new Error("Provider secret must not be exposed"); },
  });
  assert.equal(translated.outputs.unifiedInsight.insight.headline, original.outputs.unifiedInsight.insight.headline);
  assert.deepEqual(translated.outputs, original.outputs);
  assert.equal(translated.localization.status, "unavailable");
  assert.ok(!JSON.stringify(translated).includes("Provider secret"));
});

test("a translation with changed figures or ticker is rejected instead of shown to an investor", () => {
  assert.equal(validTranslation("JKH.N0000 price is LKR 19.80, +5.00%", "මිල JKH.N0000 LKR 19.80, +5.00%", "si"), true);
  assert.equal(validTranslation("Price LKR 19.80", "මිල LKR 28.00", "si"), false);
  assert.equal(validTranslation("Price LKR 19.80", "මිල USD 19.80", "si"), false);
  assert.equal(validTranslation("JKH.N0000 price 19.80", "தமிழ் BIL.N0000 19.80", "ta"), false);
  assert.equal(validTranslation("Price 19.80", "English price 19.80", "si"), false);
  assert.equal(validTranslation("Price 19.80", "", "si"), false);
  assert.equal(validTranslation("John Keells Holdings PLC has risks.", "අවදානම Company", "si", ["John Keells Holdings PLC"]), false);
});

test("invalid or incomplete provider output produces a partial translation, never fabricated text", async () => {
  const translated = await translateAnalysis(fixture(), "ta", {
    now: Date.now() + 7200000,
    translateBatch: async (texts) => Object.fromEntries(texts.map((text, i) => [String(i), text.includes("45%") ? "தமிழ் 99%" : `தமிழ் ${text}`])),
  });
  assert.equal(translated.outputs.report.insight.investor_friendly_insight.summary, "Revenue increased 45%.");
  assert.equal(translated.localization.status, "partial");
});

test("simultaneous duplicate requests share one provider call and subsequent requests use bounded cache", async () => {
  let calls = 0;
  const analysis = { outputs: { unifiedInsight: { insight: { headline: "A unique cached explanation." } } } };
  const options = { translateBatch: async (texts) => {
    calls++;
    return Object.fromEntries(texts.map((text, i) => [String(i), `සිංහල ${text}`]));
  } };
  const [first, second] = await Promise.all([
    translateAnalysis(analysis, "si", options), translateAnalysis(analysis, "si", options),
  ]);
  assert.equal(calls, 1);
  assert.deepEqual(first, second);
  assert.deepEqual(await translateAnalysis(analysis, "si", options), first);
  assert.equal(calls, 1);
});
