// Source-only audit: does not modify MongoDB or train 302 models in a batch.
require("dotenv").config({ quiet: true });
const fs = require("fs/promises");
const path = require("path");
const { fetchCompanyDirectory } = require("../src/services/companyDirectoryService");
const { prepareStock } = require("../src/services/stockPreparationService");

const main = async () => {
  const args = process.argv.slice(2);
  const symbols = args.filter((arg) => /^[A-Z0-9]+\.[NX][0-9]{4}$/.test(arg));
  if (!symbols.length && !args.includes("--all")) throw new Error("Supply CSE symbols or --all.");
  const directory = await fetchCompanyDirectory();
  const companies = directory.companies.filter((company) => !symbols.length || symbols.includes(company.symbol));
  const outputPath = path.resolve(__dirname, "../../output/cse-listing-history-audit.json");
  const results = [];
  let cursor = 0;
  const snapshot = () => ({ capturedAt: new Date().toISOString(), scope: "Source/data eligibility only; this is not forecast-accuracy validation.",
    directoryComplete: directory.complete, total: companies.length, checked: results.length,
    forecastDataReady: results.filter((row) => row.forecastReady).length, results: [...results].sort((a, b) => a.symbol.localeCompare(b.symbol)) });
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  // One writer avoids concurrent checkpoint corruption.
  let writes = Promise.resolve();
  const worker = async () => {
    while (cursor < companies.length) {
      const company = companies[cursor++];
      let result;
      try {
        result = await prepareStock({ symbol: company.symbol, company, apply: false }, {
          StockModel: { find: () => ({ sort: () => ({ lean: async () => [] }) }) },
        });
      } catch (error) { result = { symbol: company.symbol, forecastReady: false, reason: error.message }; }
      results.push(result);
      console.log(`${results.length}/${companies.length} ${company.symbol}: ${result.forecastReady ? `${result.validRows} real sessions` : result.reason || `${result.validRows} sessions; insufficient history/activity`}`);
      const serialized = JSON.stringify(snapshot(), null, 2);
      writes = writes.then(() => fs.writeFile(outputPath, serialized));
      await writes;
    }
  };
  await Promise.all([worker(), worker()]);
  console.log(JSON.stringify({ ...snapshot(), results: undefined, outputPath }));
};
main().catch((error) => { console.error(error.message); process.exitCode = 1; });
