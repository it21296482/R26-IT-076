const test = require("node:test");
const assert = require("node:assert/strict");

const {
  analyzeSentiment,
  deduplicateNews,
  describeAssociation,
  eventTags,
  pearsonCorrelation,
} = require("../src/services/externalContextService");

test("financial language receives a transparent sentiment label", () => {
  assert.equal(analyzeSentiment("Record profit and strong revenue growth").label, "positive");
  assert.equal(analyzeSentiment("Losses increased during a weak and volatile period").label, "negative");
  assert.equal(analyzeSentiment("The company published its report").label, "neutral");
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

