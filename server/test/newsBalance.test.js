const test = require("node:test");
const assert = require("node:assert/strict");
const { balancedNewsSelection, eventTags } = require("../src/services/externalContextService");

test("company headlines cannot crowd all global and disaster evidence out of the fusion input", () => {
  const feeds = ["company", "market", "global", "disaster"].map((scope) => ({ status: "fulfilled",
    value: Array.from({ length: 30 }, (_, index) => ({ title: `${scope} story ${index}`, scope, publishedAt: "2026-10-16" })) }));
  const chosen = balancedNewsSelection(feeds);
  assert.equal(chosen.length, 30);
  for (const scope of ["company", "market", "global", "disaster"]) {
    assert.ok(chosen.slice(0, 12).some((item) => item.scope === scope));
  }
  assert.equal(new Set(chosen.map((item) => item.title)).size, chosen.length);
});

test("disaster tags recognize Ditwah and recovery without labelling every story geopolitical", () => {
  const tags = eventTags("Cyclone Ditwah flooding and reconstruction affect transport");
  assert.ok(tags.includes("disaster_recovery"));
  assert.ok(!tags.includes("geopolitical"));
  assert.deepEqual(balancedNewsSelection([{ status: "rejected", reason: new Error("offline") }]), []);
});
