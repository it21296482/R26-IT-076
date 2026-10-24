require("dotenv").config({ quiet: true });
const fs = require("fs/promises");
const path = require("path");
const mongoose = require("mongoose");
const User = require("../src/models/User");
const { ensureStockPrepared } = require("../src/services/stockPreparationService");
const { loadMarketInsight } = require("../src/services/marketInsightService");
const { collectMarketRiskContext } = require("../src/services/externalContextService");
const { assessRiskImpact } = require("../src/services/riskImpactService");

const main = async () => {
  const symbol = process.argv[2];
  if (!/^[A-Z0-9]+\.[NX][0-9]{4}$/.test(symbol || "")) throw new Error("Supply an exact CSE security symbol.");
  await mongoose.connect(process.env.MONGODB_URI);
  const user = await User.findOne({ role: "admin" }).select("_id").lean();
  if (!user) throw new Error("An existing administrator is required for this local data-preparation verification.");
  const preparation = await ensureStockPrepared({ symbol, createdBy: user._id });
  if (!preparation.forecastReady) throw new Error("This security does not meet the forecast data requirements.");
  const market = await loadMarketInsight(symbol, {
    refreshHistory: async () => ({ applied: true, source: preparation.sourceNote || "existing history" }),
  });
  const context = await collectMarketRiskContext({ symbol });
  const risk = await assessRiskImpact({ symbol, marketRiskContext: context });
  const result = { symbol, verifiedAt: new Date().toISOString(), preparation, market, risk,
    scope: "Real preparation, fresh four-horizon forecast/anomaly pipeline and stock-specific risk fit. Report upload/news integration is not claimed by this test." };
  const outputPath = path.resolve(__dirname, `../../output/live-stock-${symbol}.json`);
  await fs.writeFile(outputPath, JSON.stringify(result, null, 2), { mode: 0o600 });
  console.log(JSON.stringify({ symbol, sessions: market.historical_row_count, runMode: market.run_mode,
    forecastHorizons: market.horizons?.map((item) => item.key), risk: risk.risk_level,
    riskFit: risk.training?.fresh_fit, outputPath }));
};
main().catch((error) => { console.error(error.message); process.exitCode = 1; }).finally(() => mongoose.disconnect());
