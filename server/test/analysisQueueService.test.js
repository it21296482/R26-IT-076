const test = require("node:test");
const assert = require("node:assert/strict");
const { createAnalysisQueue } = require("../src/services/analysisQueueService");

test("bounds training work, rejects duplicate users and resumes queued work after failure", async () => {
  const run = createAnalysisQueue({ concurrency: 1, maxWaiting: 1 });
  let release, started = false, queued = false;
  const first = run("one", () => new Promise((resolve) => { release = resolve; }));
  const second = run("two", async () => { started = true; throw new Error("training failed"); }, () => { queued = true; });
  const secondCheck = assert.rejects(second, /training failed/);
  assert.equal(queued, true);
  assert.equal(started, false);
  await assert.rejects(() => run("one", async () => {}), { statusCode: 409 });
  await assert.rejects(() => run("three", async () => {}), { statusCode: 503 });
  release("done");
  assert.equal(await first, "done");
  await secondCheck;
  assert.equal(started, true);
  assert.equal(await run("two", async () => "retry"), "retry");
});
