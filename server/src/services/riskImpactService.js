const { execFile } = require("child_process");
const fs = require("fs/promises");
const os = require("os");
const path = require("path");
const { promisify } = require("util");
const Stock = require("../models/Stock");

const execFileAsync = promisify(execFile);
const RISK_SCRIPT = path.resolve(__dirname, "../../../research/component4/predict_risk.py");

const sampleStandardDeviation = (values) => {
  if (values.length < 2) return null;
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / (values.length - 1);
  return Math.sqrt(variance);
};

const factorValue = (externalContext, key) => {
  const factor = externalContext?.externalFactors?.factors?.find((item) => item.key === key);
  return Number.isFinite(Number(factor?.latestValue)) ? Number(factor.latestValue) : null;
};

const buildRiskFeatures = ({ symbol, rows, externalContext }) => {
  if (rows.length < 51) {
    throw new Error("At least 51 stored price observations are required for the risk assessment.");
  }
  const latest = rows[0];
  const previous = rows.slice(1);
  const previous10 = previous.slice(0, 10).map((row) => Number(row.close));
  const previous50 = previous.slice(0, 50).map((row) => Number(row.close));
  const gold = factorValue(externalContext, "gold");
  const oil = factorValue(externalContext, "oil");
  const vix = factorValue(externalContext, "vix");
  const values = {
    stock: String(symbol).toUpperCase().split(".")[0],
    close: Number(latest.close),
    volume: Number(latest.volume),
    ma10: previous10.reduce((sum, value) => sum + value, 0) / previous10.length,
    ma50: previous50.reduce((sum, value) => sum + value, 0) / previous50.length,
    volatility: sampleStandardDeviation(previous10),
    gold,
    oil,
    vix,
    stock_date: new Date(latest.tradeDate).toISOString().slice(0, 10),
    factor_dates: Object.fromEntries(
      (externalContext?.externalFactors?.factors || [])
        .filter((item) => ["gold", "oil", "vix"].includes(item.key))
        .map((item) => [item.key, item.latestDate])
    ),
  };
  if (!Object.values(values).slice(1, 9).every(Number.isFinite)) {
    throw new Error("Current stock, gold, oil, and VIX values are required for the risk assessment.");
  }
  return values;
};

const executeRiskAssessment = async (features) => {
  const temporaryDirectory = await fs.mkdtemp(path.join(os.tmpdir(), "cse-risk-"));
  const inputPath = path.join(temporaryDirectory, "risk-input.json");
  try {
    await fs.writeFile(inputPath, JSON.stringify(features), { encoding: "utf8", mode: 0o600 });
    const { stdout } = await execFileAsync(
      process.env.PYTHON_BIN || "python",
      [RISK_SCRIPT, "--input", inputPath],
      {
        cwd: path.dirname(RISK_SCRIPT),
        timeout: Number(process.env.RISK_ANALYSIS_TIMEOUT_MS || 120000),
        maxBuffer: 4 * 1024 * 1024,
      }
    );
    const output = String(stdout || "").trim().split(/\r?\n/).at(-1);
    return JSON.parse(output);
  } finally {
    await fs.rm(temporaryDirectory, { recursive: true, force: true });
  }
};

const assessRiskImpact = async (
  { symbol, externalContext },
  { StockModel = Stock, executeRisk = executeRiskAssessment } = {}
) => {
  const rows = await StockModel.find({ symbol: String(symbol).toUpperCase() })
    .sort({ tradeDate: -1 })
    .limit(51)
    .lean();
  const result = await executeRisk(buildRiskFeatures({ symbol, rows, externalContext }));
  if (result.status !== "completed") {
    const error = new Error(result.message || "The risk assessment is unavailable for this stock.");
    error.code = result.code || "RISK_ASSESSMENT_UNAVAILABLE";
    throw error;
  }
  return result;
};

module.exports = {
  assessRiskImpact,
  buildRiskFeatures,
  executeRiskAssessment,
  sampleStandardDeviation,
};
