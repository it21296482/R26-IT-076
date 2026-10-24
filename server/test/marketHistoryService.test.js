const test = require("node:test");
const assert = require("node:assert/strict");
const { planHistoryBackfill, refreshStockHistory, validRow } = require("../src/services/marketHistoryService");

const symbol = "JKH.N0000";
const existing = [{ _id: "old", symbol, companyName: "John Keells Holdings PLC", tradeDate: new Date("2026-08-28"),
  updatedAt: new Date("2026-08-29"), open: 19.8, high: 19.9, low: 19.7, close: 19.8, volume: 1000,
  source: "csv-upload:original.csv", createdBy: "admin" }];
const point = (date, fields = {}) => ({ id: 297, t: Date.parse(`${date}T00:00:00+05:30`),
  o: null, h: 19.7, l: 19.5, p: 19.5, q: 1321052, ...fields });
const opening = (date, fields = {}) => ({ date, open: 19.5, high: 19.7, low: 19.5,
  close: 19.6, volume: 500000, ...fields });
const options = (extra = {}) => ({ symbol, existing, official: [point("2026-09-02")],
  openings: [opening("2026-09-02")], from: "2026-08-29", today: "2026-10-18", ...extra });

test("uses actual secondary opening only; CSE closing price and total volume win", () => {
  const plan = planHistoryBackfill(options());
  const row = plan.changes[0].row;
  assert.equal(row.close, 19.5);
  assert.equal(row.volume, 1321052);
  assert.equal(row.open, 19.5);
  assert.equal(row.adjustedClose, null);
  assert.equal(row.source, "cse-chart-history+tradingview-open");
  assert.deepEqual(plan.unresolved, []);
});

test("never manufactures an opening, a holiday or a weekend row", () => {
  const plan = planHistoryBackfill(options({ openings: [] }));
  assert.equal(plan.changes.length, 0);
  assert.deepEqual(plan.unresolved, ["2026-09-02"]);
  assert.equal(plan.observedDates.length, 1);
});

test("a completed backfill is idempotent and needs no further opening-price fetch", () => {
  const initial = planHistoryBackfill(options());
  const repeated = planHistoryBackfill(options({ existing: [...existing, initial.changes[0].row], openings: [] }));
  assert.equal(repeated.changes.length, 0);
  assert.deepEqual(repeated.unresolved, []);
});

test("rejects null prices, bad volumes, inconsistent OHLC and mismatching source ranges", () => {
  for (const bad of [{ open: null }, { low: 0 }, { close: NaN }, { volume: -1 }, { volume: 1.5 }, { high: 19 }]) {
    assert.equal(validRow({ ...opening("2026-09-02"), ...bad }), false);
  }
  for (const fields of [{ high: 19.8 }, { low: 19.4 }, { open: 19.8 }]) {
    const plan = planHistoryBackfill(options({ openings: [opening("2026-09-02", fields)] }));
    assert.equal(plan.changes.length, 0);
    assert.deepEqual(plan.unresolved, ["2026-09-02"]);
  }
});

test("repairs invalid and partial CSE snapshots, preserving their genuine opening", () => {
  const before = { ...existing[0], tradeDate: new Date("2026-09-02"), source: "cse-live-trade-summary", close: 0, low: 0, open: 19.5 };
  let plan = planHistoryBackfill(options({ existing: [...existing, before], openings: [] }));
  assert.equal(plan.changes[0].reason, "invalid_session");
  assert.equal(plan.changes[0].before.close, 0);
  assert.equal(plan.changes[0].row.open, 19.5);
  plan = planHistoryBackfill(options({ existing: [...existing, { ...before, low: 19.5, close: 19.6 }] }));
  assert.equal(plan.changes[0].reason, "finalized_cse_snapshot");
});

test("does not overwrite valid user imports or already reconciled history", () => {
  const before = { ...existing[0], tradeDate: new Date("2026-09-02"), ...opening("2026-09-02") };
  let plan = planHistoryBackfill(options({ existing: [...existing, before] }));
  assert.equal(plan.changes.length, 0);
  assert.deepEqual(plan.preservedConflicts, ["2026-09-02"]);
  plan = planHistoryBackfill(options({ existing: [...existing, { ...before, close: 19.5, volume: 1321052 }] }));
  assert.equal(plan.changes.length, 0);
  assert.deepEqual(plan.preservedConflicts, []);
});

test("excludes current-day observations, refuses duplicate dates", () => {
  const plan = planHistoryBackfill(options({ today: "2026-09-02" }));
  assert.equal(plan.changes.length, 0);
  assert.throws(() => planHistoryBackfill(options({ official: [point("2026-09-02"), point("2026-09-02")] })), /Duplicate/);
  assert.throws(() => planHistoryBackfill(options({ openings: [opening("2026-09-02"), opening("2026-09-02")] })), /Duplicate/);
});

const mocks = () => {
  const calls = [];
  return { calls, StockModel: { find: () => ({ sort: () => ({ lean: async () => existing }) }),
    bulkWrite: async (ops) => { calls.push({ write: ops }); return { upsertedCount: 1, modifiedCount: 0 }; } },
  fetchOfficial: async () => ({ symbol, payload: { chartData: [point("2026-09-02")] } }),
  fetchOpenings: async () => ({ symbol, rows: [opening("2026-09-02")] }),
  writeAudit: async (audit) => { calls.push({ audit }); return "/private/audit.json"; }, now: new Date("2026-10-18") };
};

test("persists source evidence and pre-images before writes; missing dates use insert-only upserts", async () => {
  const inputs = mocks();
  const result = await refreshStockHistory(symbol, inputs);
  assert.equal(inputs.calls[0].audit.changes.length, 1);
  assert.equal(inputs.calls[0].audit.sourceSha256.length, 64);
  assert.ok(inputs.calls[1].write[0].updateOne.update.$setOnInsert);
  assert.equal(result.inserted, 1);
});

test("dry-run makes no writes, failed audit prevents writes, feed failure leaves unresolved dates", async () => {
  let inputs = mocks();
  const result = await refreshStockHistory(symbol, { ...inputs, apply: false });
  assert.equal(result.applied, false);
  assert.equal(inputs.calls.length, 1);
  inputs = mocks();
  await assert.rejects(() => refreshStockHistory(symbol, { ...inputs, writeAudit: async () => { throw new Error("disk full"); } }), /disk full/);
  assert.equal(inputs.calls.length, 0);
  inputs = mocks();
  const unavailable = await refreshStockHistory(symbol, { ...inputs, fetchOpenings: async () => { throw new Error("unavailable"); } });
  assert.deepEqual(unavailable.unresolvedDates, ["2026-09-02"]);
  assert.equal(inputs.calls.length, 0);
});
