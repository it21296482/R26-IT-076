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

const factorValue = (marketRiskContext, key) => {
  const factor = marketRiskContext?.externalFactors?.factors?.find((item) => item.key === key);
  return Number.isFinite(Number(factor?.latestValue)) ? Number(factor.latestValue) : null;
};

const factorChange = (marketRiskContext, key) => {
  const factor = marketRiskContext?.externalFactors?.factors?.find((item) => item.key === key);
  return Number.isFinite(Number(factor?.change30dPct)) ? Number(factor.change30dPct) : null;
};

const median = (values) => {
  if (!values.length) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
};

const buildRiskFeatures = ({ symbol, rows, marketRiskContext, externalContext }) => {
  const context = marketRiskContext || externalContext;
  if (rows.length < 51) {
    throw new Error("At least 51 stored price observations are required for the risk assessment.");
  }
  const latest = rows[0];
  const previous = rows.slice(1);
  const previous10 = previous.slice(0, 10).map((row) => Number(row.close));
  const previous50 = previous.slice(0, 50).map((row) => Number(row.close));
  const previous20Volumes = previous.slice(0, 20).map((row) => Number(row.volume));
  const latest20Closes = rows.slice(0, 20).map((row) => Number(row.close));
  const gold = factorValue(context, "gold");
  const oil = factorValue(context, "oil");
  const vix = factorValue(context, "vix");
  const ma10 = previous10.reduce((sum, value) => sum + value, 0) / previous10.length;
  const ma50 = previous50.reduce((sum, value) => sum + value, 0) / previous50.length;
  const volatility = sampleStandardDeviation(previous10);
  const prior20Close = Number(rows[20].close);
  const previousVolumeMedian = median(previous20Volumes);
  const values = {
    stock: String(symbol).toUpperCase().split(".")[0],
    close: Number(latest.close),
    volume: Number(latest.volume),
    ma10,
    ma50,
    volatility,
    return20_pct: ((Number(latest.close) / prior20Close) - 1) * 100,
    drawdown20_pct: ((Number(latest.close) / Math.max(...latest20Closes)) - 1) * 100,
    volatility_pct: (volatility / ma10) * 100,
    volume_ratio20: previousVolumeMedian > 0 ? Number(latest.volume) / previousVolumeMedian : null,
    gold,
    oil,
    vix,
    gold_change30d_pct: factorChange(context, "gold"),
    oil_change30d_pct: factorChange(context, "oil"),
    vix_change30d_pct: factorChange(context, "vix"),
    stock_date: new Date(latest.tradeDate).toISOString().slice(0, 10),
    factor_dates: Object.fromEntries(
      (context?.externalFactors?.factors || [])
        .filter((item) => ["gold", "oil", "vix"].includes(item.key))
        .map((item) => [item.key, item.latestDate])
    ),
  };
  const requiredValues = [
    values.close, values.volume, values.ma10, values.ma50, values.volatility,
    values.return20_pct, values.drawdown20_pct, values.volatility_pct,
    values.volume_ratio20, values.gold, values.oil, values.vix,
    values.gold_change30d_pct, values.oil_change30d_pct, values.vix_change30d_pct,
  ];
  if (!requiredValues.every(Number.isFinite)) {
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
  { symbol, marketRiskContext, externalContext },
  { StockModel = Stock, executeRisk = executeRiskAssessment } = {}
) => {
  const rows = await StockModel.find({ symbol: String(symbol).toUpperCase() })
    .sort({ tradeDate: -1 })
    .limit(51)
    .lean();
  const result = await executeRisk(buildRiskFeatures({ symbol, rows, marketRiskContext, externalContext }));
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
  median,
  sampleStandardDeviation,
};
