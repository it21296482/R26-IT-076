const { execFile } = require("child_process");
const path = require("path");
const { promisify } = require("util");

const execFileAsync = promisify(execFile);
const REPORT_SCRIPT = path.resolve(__dirname, "../../../component_2/src/analyze_uploaded_report.py");

const analyzeFinancialReport = async ({ pdfPath, companyName, symbol }) => {
  const { stdout } = await execFileAsync(
    process.env.PYTHON_BIN || "python",
    [REPORT_SCRIPT, "--pdf", path.resolve(pdfPath), "--company-name", companyName, "--symbol", symbol],
    {
      cwd: path.dirname(path.dirname(REPORT_SCRIPT)),
      env: process.env,
      timeout: 3 * 60 * 1000,
      maxBuffer: 8 * 1024 * 1024,
    }
  );

  const output = String(stdout || "").trim();
  if (!output) {
    throw new Error("Financial report processing returned no result.");
  }

  try {
    return JSON.parse(output.split(/\r?\n/).at(-1));
  } catch {
    throw new Error("Financial report processing returned invalid JSON.");
  }
};

module.exports = { analyzeFinancialReport };
