const fs = require("fs/promises");
const path = require("path");
const mongoose = require("mongoose");
require("dotenv").config();

const Stock = require("../src/models/Stock");

const OUTPUT_PATH = path.resolve(
  process.argv[2] || path.join(__dirname, "../../research/component4/data/cse_stock_history.csv")
);
const SYMBOLS = ["BIL.N0000", "JKH.N0000"];

const csvValue = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;

const run = async () => {
  if (!process.env.MONGODB_URI) throw new Error("MONGODB_URI is required.");
  await mongoose.connect(process.env.MONGODB_URI);
  const rows = await Stock.find({ symbol: { $in: SYMBOLS } })
    .sort({ symbol: 1, tradeDate: 1 })
    .select("symbol tradeDate close volume -_id")
    .lean();
  if (!rows.length) throw new Error("No BIL or JKH history was found in MongoDB.");

  const lines = ["Symbol,Date,Close,Volume"];
  for (const row of rows) {
    lines.push([
      csvValue(row.symbol),
      csvValue(new Date(row.tradeDate).toISOString().slice(0, 10)),
      Number(row.close),
      Number(row.volume),
    ].join(","));
  }
  await fs.mkdir(path.dirname(OUTPUT_PATH), { recursive: true });
  await fs.writeFile(OUTPUT_PATH, `${lines.join("\n")}\n`, "utf8");
  console.info(`Exported ${rows.length} rows to ${OUTPUT_PATH}`);
};

run()
  .catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  })
  .finally(async () => mongoose.disconnect());
