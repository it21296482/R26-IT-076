const { execFile } = require("child_process");
const path = require("path");
const { promisify } = require("util");

const execFileAsync = promisify(execFile);
const INSPECTION_SCRIPT = path.resolve(__dirname, "../../../component_2/src/inspect_uploaded_report.py");

const inspectFinancialReport = async ({ pdfPath, companyName, symbol }) => {
  const { stdout } = await execFileAsync(
    process.env.PYTHON_BIN || "python",
    [INSPECTION_SCRIPT, "--pdf", path.resolve(pdfPath), "--company-name", companyName, "--symbol", symbol],
    { cwd: path.dirname(path.dirname(INSPECTION_SCRIPT)), env: process.env, timeout: 60_000 }
  );
  const output = String(stdout || "").trim().split(/\r?\n/).at(-1);
  if (!output) throw new Error("The uploaded report could not be inspected.");
  return JSON.parse(output);
};

module.exports = { inspectFinancialReport };
