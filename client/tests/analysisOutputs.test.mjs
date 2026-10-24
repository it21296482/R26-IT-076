import test from "node:test";
import assert from "node:assert/strict";
import { ANALYSIS_OUTPUTS, outputVisibility } from "../src/lib/analysisOutputs.js";

test("each of the five analysis filters shows only its own output", () => {
  assert.equal(ANALYSIS_OUTPUTS.length, 5);
  for (const { key } of ANALYSIS_OUTPUTS) {
    assert.deepEqual(Object.entries(outputVisibility(key)).filter(([, value]) => value).map(([name]) => name), [key]);
  }
});

test("initial and unknown filters preserve the complete one-page analysis", () => {
  assert.ok(Object.values(outputVisibility("")).every(Boolean));
  assert.ok(Object.values(outputVisibility("unknown")).every(Boolean));
});

test("controls are distinct and include both price panels and both overall panels", () => {
  assert.equal(new Set(ANALYSIS_OUTPUTS.map(({ controls }) => controls)).size, 5);
  assert.equal(ANALYSIS_OUTPUTS.find(({ key }) => key === "market").controls, "section-market section-market-check");
  assert.equal(ANALYSIS_OUTPUTS.find(({ key }) => key === "overall").controls, "section-overall-balance section-overall");
});

test("repeated selection and switching cannot leak another tab's content", () => {
  for (const key of ["report", "report", "news", "risk", "overall", "market", "overall"]) {
    const visible = outputVisibility(key);
    assert.equal(Object.values(visible).filter(Boolean).length, 1);
    assert.equal(visible[key], true);
  }
});
