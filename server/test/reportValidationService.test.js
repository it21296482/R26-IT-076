const test = require("node:test");
const assert = require("node:assert/strict");
const { inspectFinancialReport } = require("../src/services/reportValidationService");

test("a private PDF missing on this server requests re-upload without exposing another member's filesystem", async () => {
  const result = await inspectFinancialReport({ pdfPath: "/nonexistent/private-report.pdf", companyName: "Example PLC", symbol: "EXAMPLE.N0000" });
  assert.equal(result.accepted, false);
  assert.match(result.message, /upload.*again/);
  assert.doesNotMatch(result.message, /nonexistent|private-report.pdf/);
});
