const test = require("node:test");
const assert = require("node:assert/strict");
const { updateProgress, subscribeProgress } = require("../src/services/analysisProgressService");

test("progress is monotonic, bounded and isolated by user", () => {
  const first = [], second = [];
  const stop1 = subscribeProgress("owner-a", "same-id", (s) => first.push(s));
  const stop2 = subscribeProgress("owner-b", "same-id", (s) => second.push(s));
  updateProgress("owner-a", "same-id", { percent: 45, stage: "sequence_training" });
  updateProgress("owner-a", "same-id", { percent: 10, stage: "sequence_training" });
  assert.equal(first.at(-1).percent, 45);
  assert.equal(second.at(-1).percent, 0);
  updateProgress("owner-a", "same-id", { percent: 120, stage: "completed" });
  assert.equal(first.at(-1).percent, 100);
  stop1(); stop2();
});

test("progress resumes from the latest stage and unsubscribe stops delivery", () => {
  updateProgress("owner", "resume", { percent: 70, stage: "forecast_training" });
  const updates = [];
  const stop = subscribeProgress("owner", "resume", (s) => updates.push(s));
  assert.equal(updates[0].percent, 70);
  stop();
  updateProgress("owner", "resume", { percent: 100, stage: "completed" });
  assert.equal(updates.length, 1);
});
