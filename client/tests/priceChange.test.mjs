import test from "node:test";
import assert from "node:assert/strict";
import { priceChangeClass } from "../src/lib/priceChange.js";

test("positive percentage changes are green; negative changes are red", () => {
  assert.equal(priceChangeClass(0.01), "text-emerald-700");
  assert.equal(priceChangeClass(-0.01), "text-red-700");
});

test("unchanged and missing changes keep the existing neutral appearance", () => {
  for (const change of [0, -0, null, undefined, NaN, Infinity, "1"]) {
    assert.equal(priceChangeClass(change), "");
  }
});
