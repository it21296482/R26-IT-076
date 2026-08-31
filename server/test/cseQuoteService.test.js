const test = require("node:test");
const assert = require("node:assert/strict");

const {
  quoteToStockRow,
  refreshAvailableStockQuotes,
  tradeDateFromTimestamp,
} = require("../src/services/cseQuoteService");

test("normalizes an official CSE timestamp to the Colombo trading date", () => {
  assert.equal(tradeDateFromTimestamp(1788166790906).toISOString(), "2026-08-31T00:00:00.000Z");
});

test("maps a CSE trade-summary quote into a valid stock row", () => {
  const row = quoteToStockRow({
    symbol: "JKH.N0000",
    name: "JOHN KEELLS HOLDINGS PLC",
    closingPrice: 19.8,
    open: 20,
    high: 20.1,
    low: 19.7,
    sharevolume: 123456,
    lastTradedTime: 1788166790906,
  }, {
    symbol: "JKH.N0000",
    companyName: "John Keells Holdings PLC",
    createdBy: "admin-id",
  });

  assert.equal(row.close, 19.8);
  assert.equal(row.volume, 123456);
  assert.equal(row.source, "cse-live-trade-summary");
  assert.equal(row.tradeDate.toISOString(), "2026-08-31T00:00:00.000Z");
});

test("refreshes every stock already available in the application from one quote response", async () => {
  let operations = [];
  const StockModel = {
    aggregate: async () => [
      { symbol: "JKH.N0000", companyName: "John Keells Holdings PLC", tradeDate: new Date("2026-08-28"), createdBy: "one" },
      { symbol: "BIL.N0000", companyName: "Browns Investments PLC", tradeDate: new Date("2026-08-28"), createdBy: "one" },
    ],
    bulkWrite: async (value) => { operations = value; },
  };
  const quote = (symbol, name, price) => ({
    symbol,
    name,
    closingPrice: price,
    open: price,
    high: price,
    low: price,
    sharevolume: 1000,
    lastTradedTime: 1788166790906,
  });
  const result = await refreshAvailableStockQuotes({
    StockModel,
    fetchQuotes: async () => [
      quote("JKH.N0000", "JOHN KEELLS HOLDINGS PLC", 19.8),
      quote("BIL.N0000", "BROWNS INVESTMENTS PLC", 5.1),
    ],
  });

  assert.equal(operations.length, 2);
  assert.deepEqual(result.updatedSymbols, ["JKH.N0000", "BIL.N0000"]);
  assert.ok(operations.every((operation) => operation.updateOne.upsert));
});
