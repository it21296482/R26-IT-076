const { execFile } = require("child_process");
const fs = require("fs/promises");
const os = require("os");
const path = require("path");
const { promisify } = require("util");
const Stock = require("../models/Stock");

const execFileAsync = promisify(execFile);
const ANALYSIS_SCRIPT = path.resolve(
  __dirname,
  "../../../research/component1/analyze_market_on_demand.py"
);
const MINIMUM_HISTORY_ROWS = 300;

const stockCodeFromSymbol = (symbol) => String(symbol || "").toUpperCase().split(".")[0];

const csvCell = (value) => {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

const historyCsv = (rows) => [
  "date,symbol,open,high,low,close,volume,source",
  ...rows.map((row) => [
    new Date(row.tradeDate).toISOString().slice(0, 10),
    row.symbol,
    row.open,
    row.high,
    row.low,
    row.close,
    row.volume,
    row.source || "mongodb",
  ].map(csvCell).join(",")),
].join("\n");

const executeFreshAnalysis = async ({ inputPath, outputPath, stockCode }) => {
  await execFileAsync(process.env.PYTHON_BIN || "python", [
    ANALYSIS_SCRIPT,
    "--input-csv", inputPath,
    "--stock", stockCode,
    "--output", outputPath,
    "--epochs", process.env.MARKET_ANALYSIS_EPOCHS || "18",
  ], {
    cwd: path.dirname(ANALYSIS_SCRIPT),
    timeout: Number(process.env.MARKET_ANALYSIS_TIMEOUT_MS || 360000),
    maxBuffer: 10 * 1024 * 1024,
  });
};

const loadMarketInsight = async (
  symbol,
  { StockModel = Stock, executeAnalysis = executeFreshAnalysis } = {}
) => {
  const normalizedSymbol = String(symbol || "").toUpperCase();
  const stockCode = stockCodeFromSymbol(symbol);
  const rows = await StockModel.find({ symbol: normalizedSymbol })
    .sort({ tradeDate: 1 })
    .lean();
  if (rows.length < MINIMUM_HISTORY_ROWS) {
    const unavailableError = new Error(
      `At least ${MINIMUM_HISTORY_ROWS} historical sessions are required for ${normalizedSymbol}.`
    );
    unavailableError.code = "MARKET_HISTORY_INSUFFICIENT";
    throw unavailableError;
  }

  const tempDirectory = await fs.mkdtemp(path.join(os.tmpdir(), `cse-market-${stockCode.toLowerCase()}-`));
  const inputPath = path.join(tempDirectory, `${stockCode}_latest_history.csv`);
  const outputPath = path.join(tempDirectory, "market_insight.json");
  try {
    await fs.writeFile(inputPath, historyCsv(rows), "utf8");
    await executeAnalysis({ inputPath, outputPath, stockCode });
    const payload = JSON.parse(await fs.readFile(outputPath, "utf8"));
    if (payload.symbol !== normalizedSymbol || payload.run_mode !== "fresh_on_demand") {
      throw new Error("The fresh market output did not match the selected stock.");
    }
    return payload;
  } finally {
    await fs.rm(tempDirectory, { recursive: true, force: true });
  }
};

module.exports = {
  executeFreshAnalysis,
  historyCsv,
  loadMarketInsight,
  stockCodeFromSymbol,
};
