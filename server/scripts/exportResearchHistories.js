// Research export for the Component 1 multi-stock evaluation.
// Uses the application's own source fetchers and CSE reconciliation
// (buildPreparationPlan), but writes CSV files only. MongoDB is never modified.
//
//   cd server
//   node scripts/exportResearchHistories.js --all --until 2026-08-28
//   node scripts/exportResearchHistories.js JKH.N0000 COMB.N0000 --until 2026-08-28
//
// Output: research/component1/data/actuals_all/<CODE>_actual_through_<date>.csv
//         research/component1/data/actuals_all/export_manifest.json (one row per listing,
//         including every exclusion reason, for the paper's inclusion flowchart)
require("dotenv").config({ quiet: true });
const fs = require("fs/promises");
const path = require("path");
const { createHash } = require("crypto");
const { fetchCompanyDirectory } = require("../src/services/companyDirectoryService");
const { buildPreparationPlan, fetchLongHistory } = require("../src/services/stockPreparationService");
const { fetchOfficialHistory } = require("../src/services/marketHistoryService");

const args = process.argv.slice(2);
const value = (name) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined);
const until = value("--until") || "2026-08-28";
const concurrency = Number(value("--workers") || 2);
const symbols = args.filter((arg) => /^[A-Z0-9]+\.[NX][0-9]{4}$/.test(arg));
const OUT = path.resolve(__dirname, "../../research/component1/data/actuals_all");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const toCsv = (rows) => ["date,symbol,open,high,low,close,volume,source",
  ...rows.map((r) => [r.tradeDate.toISOString().slice(0, 10), r.symbol, r.open, r.high, r.low, r.close, r.volume, r.source].join(","))]
  .join("\n") + "\n";

const main = async () => {
  if (!symbols.length && !args.includes("--all")) throw new Error("Supply CSE symbols or --all.");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(until)) throw new Error("--until must be YYYY-MM-DD.");
  const directory = await fetchCompanyDirectory();
  if (!directory.complete) console.warn(`Directory incomplete; failed letters: ${directory.failedLetters.join(",")}`);
  const companies = directory.companies.filter((c) => !symbols.length || symbols.includes(c.symbol));
  await fs.mkdir(OUT, { recursive: true });
  const manifestPath = path.join(OUT, "export_manifest.json");
  let previous = [];
  try { previous = JSON.parse(await fs.readFile(manifestPath, "utf8")).results || []; } catch { /* first run */ }
  const done = new Map(previous.filter((r) => r.status === "exported").map((r) => [r.symbol, r]));
  const results = [...done.values()];
  // "today" = the day after the cut-off, so the plan keeps sessions up to and including --until.
  const today = new Date(Date.parse(`${until}T00:00:00Z`) + 86400000).toISOString().slice(0, 10);
  let cursor = 0;
  const worker = async () => {
    while (cursor < companies.length) {
      const company = companies[cursor++];
      if (done.has(company.symbol)) continue;
      const row = { symbol: company.symbol, companyName: company.companyName };
      try {
        const history = await fetchLongHistory(company.symbol);
        const official = await fetchOfficialHistory(company.symbol, { security: { symbol: company.symbol, id: company.securityId } });
        const plan = buildPreparationPlan({ company, history, official, today, createdBy: null });
        const code = company.symbol.replace(".", "_");
        const file = `${code}_actual_through_${until}.csv`;
        const csv = toCsv(plan.rows);
        await fs.writeFile(path.join(OUT, file), csv);
        Object.assign(row, { status: "exported", file, sha256: createHash("sha256").update(csv).digest("hex"),
          rows: plan.rows.length, first: plan.rows[0]?.tradeDate.toISOString().slice(0, 10),
          last: plan.quality.latestDate, recentAgreement: plan.quality.recentAgreement,
          recentActiveSessions: plan.quality.recentActiveSessions });
      } catch (error) {
        Object.assign(row, { status: "not_exported", reason: error.message });
      }
      results.push(row);
      console.log(`${results.length}/${companies.length} ${company.symbol}: ${row.status === "exported" ? `${row.rows} rows ${row.first}..${row.last}` : row.reason}`);
      await fs.writeFile(manifestPath, JSON.stringify({ until, capturedAt: new Date().toISOString(),
        directoryComplete: directory.complete, listings: companies.length, results }, null, 2));
      await sleep(400); // be polite to public sources
    }
  };
  await Promise.all(Array.from({ length: concurrency }, worker));
  const exported = results.filter((r) => r.status === "exported").length;
  console.log(`\nExported ${exported}/${companies.length}. Manifest: ${manifestPath}`);
  console.log("Next: cd ../research/component1 && python experiments/paper_experiments.py --stocks ALL --data-dir data/actuals_all --resume");
};

main().catch((error) => { console.error(error.message); process.exitCode = 1; });
