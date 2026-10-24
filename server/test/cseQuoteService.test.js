const test = require("node:test");
const assert = require("node:assert/strict");

const {
  quoteToStockRow,
  refreshAvailableStockQuotes,
  tradeDateFromTimestamp,
  quotePriceList,
} = require("../src/services/cseQuoteService");

test("normalizes an official CSE timestamp to the Colombo trading date", () => {
  assert.equal(tradeDateFromTimestamp(1788166790906).toISOString(), "2026-08-31T00:00:00.000Z");
});

test("market list includes all returned symbols without inventing missing prices or dates", () => {
  const quotes = quotePriceList([{symbol:"JKH.N0000",name:"JOHN KEELLS HOLDINGS PLC",price:18,lastTradedTime:1792141179424},
    {symbol:"TEST.N0000",name:"TEST PLC",price:0,closingPrice:0,lastTradedTime:0}]);
  assert.equal(quotes.length,2);
  assert.equal(quotes[0].price,18);
  assert.equal(quotes[1].price,null);
  assert.equal(quotes[1].lastTradeDate,null);
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

test("unfinished zero close uses a positive last-traded price, never zero", () => {
  const quote = { closingPrice: 0, price: 19.8, open: 20, high: 20.1, low: 19.7,
    sharevolume: 1000, lastTradedTime: 1788166790906 };
  assert.equal(quoteToStockRow(quote, { symbol: "JKH.N0000" }).close, 19.8);
  assert.equal(quoteToStockRow({ ...quote, price: 0 }, { symbol: "JKH.N0000" }), null);
  assert.equal(quoteToStockRow({ ...quote, low: 0 }, { symbol: "JKH.N0000" }), null);
  assert.equal(quoteToStockRow({ ...quote, sharevolume: -1 }, { symbol: "JKH.N0000" }), null);
});
