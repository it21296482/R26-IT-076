import test from "node:test";
import assert from "node:assert/strict";
import { progressLabel, progressUrl } from "../src/lib/analysisProgress.js";
import { messages } from "../src/i18n/messages.js";

test("progress URLs support relative and absolute API configuration", () => {
  assert.equal(progressUrl("/api", "run-1", "http://localhost:5173"), "http://localhost:5173/api/analysis/progress/run-1");
  assert.equal(progressUrl("http://127.0.0.1:5001/api/", "run-1", "http://localhost:5173"), "http://127.0.0.1:5001/api/analysis/progress/run-1");
});

test("all runtime progress stages have human-readable multilingual labels", () => {
  for (const stage of ["upload","waiting","refreshing_prices","validating_report","loading_history","validating_history","building_features","sequence_training","anomaly_calibration","explanations","forecast_training","checking_output","market_complete","combining_evidence","completed","failed","market_unavailable"]) {
    assert.ok(Object.hasOwn(messages, progressLabel(stage)),stage);
  }
});
