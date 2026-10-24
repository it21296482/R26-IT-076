const { execFile } = require("child_process");
const path = require("path");
const { promisify } = require("util");
const fs = require("fs/promises");

const execFileAsync = promisify(execFile);
const INSPECTION_SCRIPT = path.resolve(__dirname, "../../../component_2/src/inspect_uploaded_report.py");

const inspectFinancialReport = async ({ pdfPath, companyName, symbol }) => {
  try { await fs.access(pdfPath); } catch {
    return { accepted: false, message: "Please upload this company's latest report again. The saved file is not available on this server." };
  }
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
