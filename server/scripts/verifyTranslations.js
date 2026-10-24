// Verify presentation translation against a saved analysis; never rerun models.
require("dotenv").config({ quiet: true });
const assert = require("node:assert/strict");
const fs = require("fs/promises");
const path = require("path");
const mongoose = require("mongoose");
const jwt = require("jsonwebtoken");
const AnalysisRun = require("../src/models/AnalysisRun");
const { validTranslation } = require("../src/services/translationService");

const main = async () => {
  await mongoose.connect(process.env.MONGODB_URI);
  const original = await AnalysisRun.findOne({ status: "completed" }).sort({ createdAt: -1 }).lean();
  if (!original) throw new Error("Complete an analysis first; translations do not recreate expired evidence.");
  const token = jwt.sign({ userId: String(original.user) }, process.env.JWT_SECRET, { expiresIn: "30m" });
  const receipts = [];
  for (const language of ["si", "ta"]) {
    const started = Date.now();
    const response = await fetch(`http://127.0.0.1:${process.env.PORT || 5001}/api/analysis/${original._id}?language=${language}`, {
      headers: { Cookie: `token=${token}` }, signal: AbortSignal.timeout(900000),
    });
    assert.equal(response.status, 200);
    const { analysis } = await response.json();
    const source = original.outputs.unifiedInsight.insight;
    const translated = analysis.outputs.unifiedInsight.insight;
    await fs.writeFile(path.resolve(__dirname, `../../output/translation-verification-${language}.json`),
      JSON.stringify({ localization: analysis.localization, original: source, translated }, null, 2), { mode: 0o600 });
    console.log(JSON.stringify(analysis.localization));
    for (const key of ["headline", "plain_language_overview", "company_report_takeaway", "non_advisory_note"]) {
      if (source[key]) assert.ok(validTranslation(source[key], translated[key], language,
        [original.companyName, original.stockSymbol]), `${language}: summary field ${key} was not translated safely`);
    }
    assert.equal(analysis.outputs.market.current_price_lkr, original.outputs.market.current_price_lkr);
    assert.equal(analysis.outputs.riskImpact.risk_level, original.outputs.riskImpact.risk_level);
    const receipt = { language, seconds: (Date.now() - started) / 1000, ...analysis.localization,
      headline: translated.headline, overviewStart: translated.plain_language_overview?.slice(0, 500) };
    receipts.push(receipt);
    console.log(JSON.stringify(receipt, null, 2));
  }
  return receipts;
};
main().catch((error) => { console.error(error.message); process.exitCode = 1; }).finally(() => mongoose.disconnect());
