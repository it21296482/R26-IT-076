import test from "node:test";
import assert from "node:assert/strict";
import { anomalyHeading } from "../src/lib/marketStatus.js";

test("missing or incomplete anomaly evidence never means normal movement", () => {
  for (const market of [null, undefined, {}, { anomaly: {} }, { anomaly: { detected: null } }]) {
    assert.equal(anomalyHeading(market), "This check was unavailable.");
  }
});

test("normal and unusual headings require an explicit completed result", () => {
  assert.equal(anomalyHeading({ anomaly: { detected: false } }), "No unusual deviation at the latest check");
  assert.equal(anomalyHeading({ anomaly: { detected: true } }), "An unusual deviation was detected");
});
