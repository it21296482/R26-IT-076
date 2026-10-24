const test = require("node:test");
const assert = require("node:assert/strict");
const { buildPreparationPlan, prepareStock, requireListedCompany } = require("../src/services/stockPreparationService");
const company = { symbol: "COMB.X0000", companyName: "Commercial Bank PLC", securityId: 123 };
const fixture = () => {
  const rows = Array.from({ length: 20 }, (_, index) => ({ date: new Date(Date.UTC(2026, 8, 27 + index)).toISOString().slice(0, 10),
    open: 18, high: 20, low: 17, close: 19, volume: 123.25 }));
  return { company, history: { symbol: company.symbol, rows }, today: "2026-10-18", createdBy: "user",
    official: { symbol: company.symbol, payload: { chartData: rows.map((row) => ({
      t: Date.parse(`${row.date}T06:00:00Z`), h: 20, l: 17, p: 18.9, q: 200, o: null })) } } };
};

test("uses actual full-symbol history and reconciles official closing prices and totals", () => {
  const result = buildPreparationPlan(fixture());
  assert.equal(result.rows.length, 20);
  assert.equal(result.rows[0].symbol, "COMB.X0000");
  assert.equal(result.rows[0].open, 18);
  assert.equal(result.rows[0].close, 18.9);
  assert.equal(result.rows[0].volume, 200);
  assert.equal(result.quality.officialReplacements, 20);
  assert.equal(result.quality.forecastReady, false);
});

test("retains explicitly sourced split-adjusted observations outside the official overlap without rounding volume", () => {
  const data = fixture();
  data.official.payload.chartData = data.official.payload.chartData.slice(5);
  const plan = buildPreparationPlan(data);
  assert.equal(plan.rows[0].volume, 123.25);
  assert.equal(plan.rows[0].close, 19);
  assert.match(plan.rows[0].notes, /not independently verified/);
});

test("never copies voting shares to a non-voting share, or admits duplicate dates", () => {
  const data = fixture();
  data.history.symbol = "COMB.N0000";
  assert.throws(() => buildPreparationPlan(data), /identity mismatch/);
  data.history.symbol = company.symbol;
  data.history.rows.push(data.history.rows[0]);
  assert.throws(() => buildPreparationPlan(data), /Duplicate/);
});

test("rejects incompatible adjustment bases and inadequate cross-source evidence", () => {
  const data = fixture();
  data.official.payload.chartData.forEach((row) => { row.h *= 2; row.l *= 2; });
  assert.throws(() => buildPreparationPlan(data), /could not be reconciled/);
  const short = fixture();
  short.official.payload.chartData = short.official.payload.chartData.slice(0, 5);
  assert.throws(() => buildPreparationPlan(short), /could not be reconciled/);
});

test("older adjusted prices stay unchanged when only the current basis is corroborated", () => {
  const data = fixture();
  const older = { ...data.history.rows[0], date: "2026-07-01" };
  data.history.rows.unshift(older);
  data.official.payload.chartData.unshift({ t: Date.parse("2026-07-01T06:00:00Z"), h: 40, l: 34, p: 38, q: 200 });
  const plan = buildPreparationPlan(data);
  assert.equal(plan.rows[0].close, 19);
  assert.equal(plan.quality.recentAgreement, 1);
  assert.ok(plan.quality.agreement < 1);
});

test("excludes incomplete current-day rows and rejects stale current history", () => {
  const data = fixture();
  data.history.rows.push({ ...data.history.rows[0], date: data.today });
  assert.equal(buildPreparationPlan(data).rows.length, 20);
  const stale = fixture();
  stale.today = "2026-12-01";
  assert.throws(() => buildPreparationPlan(stale), /Recent completed/);
});

test("source audit is read-only; names come from the official directory", async () => {
  const data = fixture();
  const loadDirectory = async () => ({ companies: [company] });
  assert.equal((await requireListedCompany(company.symbol, loadDirectory)).companyName, company.companyName);
  await assert.rejects(() => requireListedCompany("FAKE.N0000", loadDirectory), /could not be confirmed/);
  let writes = 0;
  const result = await prepareStock({ symbol: company.symbol, company, apply: false }, {
    StockModel: { find: () => ({ sort: () => ({ lean: async () => [] }) }), bulkWrite: async () => { writes += 1; } },
    fetchHistory: async () => data.history, fetchOfficial: async () => data.official,
    now: new Date("2026-10-18T00:00:00Z"),
  });
  assert.equal(result.validRows, 20);
  assert.equal(result.forecastReady, false);
  assert.equal(writes, 0);
});
