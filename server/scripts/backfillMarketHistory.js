require("dotenv").config({ quiet: true });
const mongoose = require("mongoose");
const { refreshStockHistory } = require("../src/services/marketHistoryService");

const args = process.argv.slice(2);
const value = (name) => args.includes(name) ? args[args.indexOf(name) + 1] : undefined;
const symbols = (value("--symbols") || "JKH.N0000,BIL.N0000").split(",");
const apply = args.includes("--apply");

(async () => {
  if (!process.env.MONGODB_URI) throw new Error("MONGODB_URI is required.");
  await mongoose.connect(process.env.MONGODB_URI);
  for (const symbol of symbols) {
    const result = await refreshStockHistory(symbol.trim(), { apply, from: value("--from") });
    console.log(JSON.stringify(result, null, 2));
  }
})().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
}).finally(() => mongoose.disconnect());
