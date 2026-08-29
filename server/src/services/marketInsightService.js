const fs = require("fs/promises");
const path = require("path");

const ARTIFACT_DIRECTORY = path.resolve(
  __dirname,
  "../../../research/component1/artifacts/runtime"
);

const stockCodeFromSymbol = (symbol) => String(symbol || "").toUpperCase().split(".")[0];

const loadMarketInsight = async (symbol) => {
  const stockCode = stockCodeFromSymbol(symbol);
  const artifactPath = path.join(ARTIFACT_DIRECTORY, `${stockCode.toLowerCase()}_market_insight.json`);

  try {
    const payload = JSON.parse(await fs.readFile(artifactPath, "utf8"));
    if (payload.symbol !== String(symbol).toUpperCase()) {
      throw new Error("The market artifact symbol does not match the requested stock.");
    }
    return payload;
  } catch (error) {
    if (error.code === "ENOENT") {
      const unavailableError = new Error(
        `A validated market-analysis artifact is not available for ${symbol}.`
      );
      unavailableError.code = "MARKET_ARTIFACT_UNAVAILABLE";
      throw unavailableError;
    }
    throw error;
  }
};

module.exports = { loadMarketInsight, stockCodeFromSymbol };

