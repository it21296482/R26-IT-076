const { execFile } = require("child_process");
const fs = require("fs/promises");
const os = require("os");
const path = require("path");
const { promisify } = require("util");
const Stock = require("../models/Stock");
const { refreshStockHistory } = require("./marketHistoryService");
const { MINIMUM_HISTORY_ROWS } = require("./stockCoverageService");
const { tradeDateFromTimestamp } = require("./cseQuoteService");

const execFileAsync = promisify(execFile);
const ANALYSIS_SCRIPT = path.resolve(
  __dirname,
  "../../../research/component1/analyze_market_on_demand.py"
);

const stockCodeFromSymbol = (symbol) => String(symbol || "").toUpperCase().replace(/\.N0000$/, "");

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

const executeFreshAnalysis = async ({ inputPath, outputPath, stockCode, onProgress = () => {} }) => {
  try {
    const execution = execFileAsync(process.env.PYTHON_BIN || "python", [
      ANALYSIS_SCRIPT,
      "--input-csv", inputPath,
      "--stock", stockCode,
      "--output", outputPath,
      "--epochs", process.env.MARKET_ANALYSIS_EPOCHS || "18",
    ], {
      cwd: path.dirname(ANALYSIS_SCRIPT),
      timeout: Number(process.env.MARKET_ANALYSIS_TIMEOUT_MS || 360000),
      maxBuffer: 10 * 1024 * 1024,
      env: { ...process.env, CSE_MARKET_PROGRESS: "1", PYTHONUNBUFFERED: "1",
        MPLCONFIGDIR: process.env.MPLCONFIGDIR || path.join(os.tmpdir(), "cse-market-matplotlib"), MPLBACKEND: "Agg" },
    });
    let buffer = "";
    execution.child.stdout.on("data", (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("CSE_PROGRESS ")) continue;
        try {
          const progress = JSON.parse(line.slice(13));
          if (Number.isFinite(progress.percent) && typeof progress.stage === "string") {
            console.info(`[market:${stockCode}] ${progress.stage} ${Math.round(progress.percent)}%`,
              progress.epoch ? `pass ${progress.training_pass}, epoch ${progress.epoch}/${progress.epochs}`
                : progress.selected_candidate ? `${progress.horizon} sessions: ${progress.selected_candidate} selected from ${progress.candidates_compared} candidates` : "");
            onProgress(progress);
          }
        } catch { /* Ignore non-protocol output; it must not terminate training. */ }
      }
    });
    await execution;
  } catch (cause) {
    console.error(`[market:${stockCode}] process failed`, {
      code: cause.code,
      signal: cause.signal,
      diagnostic: String(cause.stderr || cause.message || "").slice(-3000),
    });
    const error = new Error(cause.killed
      ? "The market analysis exceeded its processing time limit. Please try again."
      : "The market analysis could not finish. The server recorded the failure for review.");
    error.code = cause.killed ? "MARKET_ANALYSIS_TIMEOUT" : "MARKET_ANALYSIS_FAILED";
    error.cause = cause;
    throw error;
  }
};

const loadMarketInsight = async (
  symbol,
  { StockModel = Stock, executeAnalysis = executeFreshAnalysis, onProgress = () => {},
    refreshHistory = refreshStockHistory } = {}
) => {
  const normalizedSymbol = String(symbol || "").toUpperCase();
  const stockCode = stockCodeFromSymbol(symbol);
  onProgress({ stage: "loading_history", percent: 0 });
  let historyRefresh;
  try {
    historyRefresh = await refreshHistory(normalizedSymbol, { StockModel });
  } catch (error) {
    console.warn(`[history:${normalizedSymbol}] refresh unavailable: ${error.message}`);
    historyRefresh = { applied: false, warning: "Recent daily history could not be checked against its sources on this run. Stored observations were used without inventing missing prices." };
  }
  const rows = await StockModel.find({ symbol: normalizedSymbol, tradeDate: { $lt: tradeDateFromTimestamp(Date.now()) } })
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
    await executeAnalysis({ inputPath, outputPath, stockCode, onProgress });
    const payload = JSON.parse(await fs.readFile(outputPath, "utf8"));
    if (payload.symbol !== normalizedSymbol || payload.run_mode !== "fresh_on_demand") {
      throw new Error("The fresh market output did not match the selected stock.");
    }
    payload.history_refresh = historyRefresh;
    payload.warnings = payload.warnings || [];
    if (historyRefresh.warning) payload.warnings.push(historyRefresh.warning);
    if (historyRefresh.unresolvedDates?.length) payload.warnings.push(
      `${historyRefresh.unresolvedDates.length} recent CSE sessions still lack fully verified model inputs; no prices were invented.`);
    if (historyRefresh.preservedConflicts?.length) payload.warnings.push(
      "Some uploaded observations disagree with CSE history and were preserved for review rather than silently overwritten.");
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
