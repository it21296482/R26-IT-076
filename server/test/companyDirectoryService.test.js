const test = require("node:test");
const assert = require("node:assert/strict");
const { createDirectoryLoader, mergeCompanyUniverse } = require("../src/services/companyDirectoryService");
const { stockAvailability, getStockAvailability } = require("../src/services/stockCoverageService");

test("fetches every directory letter, deduplicates securities, caches and shares concurrent requests", async () => {
  const letters = [];
  let clock = 1000;
  const load = createDirectoryLoader({ now: () => clock, ttlMs: 100, fetchLetter: async (letter) => {
    letters.push(letter);
    return [{ symbol: "JKH.N0000", name: "JOHN KEELLS HOLDINGS PLC" },
      { symbol: "NEW.N0000", name: "NEW COMPANY PLC" }, { symbol: "", name: "invalid" }];
  } });
  const [one, two] = await Promise.all([load(), load()]);
  assert.deepEqual(letters.slice().sort(), [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"]);
  assert.equal(one, two);
  assert.equal(one.companies.length, 2);
  assert.equal(one.companies[0].companyName, "John Keells Holdings PLC");
  assert.equal(one.complete, true);
  await load();
  assert.equal(letters.length, 26);
  clock += 101;
  await load();
  assert.equal(letters.length, 52);
});

test("source failure is explicit and retains cached company names without claiming a complete refresh", async () => {
  let fail = false, clock = 1000;
  const load = createDirectoryLoader({ now: () => clock, ttlMs: 10, fetchLetter: async (letter) => {
    if (fail && letter === "A") throw new Error("timeout");
    return letter === "A" ? [{ symbol: "ABAN.N0000", name: "ABANS ELECTRICALS PLC" }]
      : letter === "B" ? [{ symbol: "BIL.N0000", name: "BROWNS INVESTMENTS PLC" }] : [];
  } });
  await load();
  fail = true; clock += 11;
  const result = await load();
  assert.equal(result.companies.length, 2);
  assert.equal(result.complete, false);
  assert.deepEqual(result.failedLetters, ["A"]);
});

test("an unavailable directory fails safely without an empty success or fabricated companies", async () => {
  const load = createDirectoryLoader({ fetchLetter: async () => { throw new Error("offline"); } });
  await assert.rejects(load, /temporarily unavailable/);
});

test("full analysis requires valid history AND actual model coverage; share classes stay distinct", () => {
  const coverage = new Set(["JKH.N0000"]);
  assert.equal(stockAvailability({ symbol: "JKH.N0000", validHistoryCount: 1000 }, coverage).analysisAvailable, true);
  assert.equal(stockAvailability({ symbol: "JKH.N0000", validHistoryCount: 999, recordCount: 2000 }, coverage).analysisStatus, "history_required");
  assert.equal(stockAvailability({ symbol: "OTHER.N0000", validHistoryCount: 3000 }, coverage).analysisStatus, "coverage_required");
  assert.equal(stockAvailability({ symbol: "JKH.X0000", validHistoryCount: 3000 }, coverage).analysisAvailable, false);
  assert.equal(stockAvailability({ symbol: "OTHER.N0000" }, coverage).analysisStatus, "history_and_coverage_required");
});

test("lists all companies as eligible for preparation without claiming pre-validated coverage or manufacturing database rows", () => {
  const companies = [{ symbol: "JKH.N0000", companyName: "John Keells Holdings PLC" },
    { symbol: "OTHER.N0000", companyName: "Other PLC" }];
  const result = mergeCompanyUniverse(companies, [{ symbol: "JKH.N0000", validHistoryCount: 3419, recordCount: 3419 }],
    new Set(["JKH.N0000"]), stockAvailability);
  assert.equal(result.length, 2);
  assert.equal(result[0].analysisAvailable, true);
  assert.equal(result[1].analysisAvailable, false);
  assert.equal(result[1].analysisEligible, true);
  assert.equal(result[1].recordCount, 0);
  assert.equal(result[1].latestClose, undefined);
});

test("server eligibility evaluates the requested symbol instead of trusting the browser", async () => {
  let pipeline;
  const availability = await getStockAvailability("OTHER.N0000", {
    StockModel: { aggregate: async (value) => { pipeline = value; return [{ symbol: "OTHER.N0000", validHistoryCount: 4000 }]; } },
    loadCoverage: async () => new Set(["JKH.N0000"]),
  });
  assert.deepEqual(pipeline[0], { $match: { symbol: "OTHER.N0000" } });
  assert.equal(availability.analysisAvailable, false);
});
