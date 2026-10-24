// Local regression using an existing user's own uploaded report. Tokens stay in
// memory and are never printed or saved with the verification result.
require("dotenv").config({ quiet: true });
const fs = require("fs/promises");
const path = require("path");
const mongoose = require("mongoose");
const jwt = require("jsonwebtoken");
const FinancialReport = require("../src/models/FinancialReport");
const User = require("../src/models/User");
const { randomUUID } = require("crypto");

const main = async () => {
  const symbol = process.argv[2];
  if (!/^[A-Z0-9]+\.[NX][0-9]{4}$/.test(symbol || "")) throw new Error("Supply an exact CSE security symbol.");
  await mongoose.connect(process.env.MONGODB_URI);
  const candidates = await FinancialReport.find({ stockSymbol: symbol }).sort({ reportingPeriodEnd: -1, createdAt: -1 }).limit(100).lean();
  let report;
  for (const candidate of candidates) {
    try { await fs.access(candidate.storagePath); report = candidate; break; } catch { /* Uploads are private to each server, not shared through Git. */ }
  }
  if (!report) throw new Error("Upload the selected company's genuine latest report before testing its complete workflow.");
  const user = await User.findOne({ _id: report.uploadedBy, role: "user" }).select("_id").lean();
  if (!user) throw new Error("The uploaded report's user account is unavailable.");
  const token = jwt.sign({ userId: String(user._id) }, process.env.JWT_SECRET, { expiresIn: "15m" });
  const started = Date.now();
  const response = await fetch(`http://127.0.0.1:${process.env.PORT || 5001}/api/analysis`, {
    method: "POST", headers: { "Content-Type": "application/json", Cookie: `token=${token}` },
    body: JSON.stringify({ stockSymbol: symbol, reportId: String(report._id), clientRequestId: randomUUID() }),
    signal: AbortSignal.timeout(600000),
  });
  const result = await response.json();
  if (response.status !== 201) throw new Error(`Analysis API returned ${response.status}: ${result.message}`);
  const analysis = result.analysis;
  const receipt = { symbol, httpStatus: response.status, status: analysis.status,
    elapsedSeconds: (Date.now() - started) / 1000, workflow: analysis.outputs.workflow,
    warnings: analysis.warnings, horizons: analysis.outputs.market?.horizons?.map((item) => item.key),
    risk: analysis.outputs.riskImpact?.risk_level, summaryStatus: analysis.outputs.unifiedInsight?.status,
    summaryGeneration: analysis.outputs.unifiedInsight?.generation,
    summaryFallback: analysis.outputs.unifiedInsight?.fallback_used,
    reportGeneration: analysis.outputs.report?.generation,
    reportFallback: analysis.outputs.report?.fallback_used };
  await fs.writeFile(path.resolve(__dirname, `../../output/api-verification-${symbol}.json`),
    JSON.stringify(receipt, null, 2), { mode: 0o600 });
  console.log(JSON.stringify(receipt, null, 2));
};
main().catch((error) => { console.error(error.message); process.exitCode = 1; }).finally(() => mongoose.disconnect());
