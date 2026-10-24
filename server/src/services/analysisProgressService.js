const records = new Map();
const TTL_MS = 30 * 60 * 1000;
const keyFor = (user, requestId) => `${user}:${requestId}`;

const progressRecord = (user, requestId) => {
  for (const [key, record] of records) {
    if (record.updatedAt < Date.now() - TTL_MS) {
      for (const listener of record.listeners) listener({ ...record.state, status: "expired" });
      records.delete(key);
    }
  }
  const key = keyFor(user, requestId);
  if (!records.has(key)) {
    if (records.size >= 1000) throw Object.assign(new Error("Progress service is busy."), { statusCode: 503 });
    records.set(key, { updatedAt: Date.now(), listeners: new Set(), state: { percent: 0, stage: "waiting", status: "waiting" } });
  }
  return records.get(key);
};

const updateProgress = (user, requestId, update) => {
  if (!requestId) return;
  const record = progressRecord(user, requestId);
  const percent = Number(update.percent);
  record.updatedAt = Date.now();
  record.state = {
    ...update, status: update.status || record.state.status,
    percent: Math.max(record.state.percent, Number.isFinite(percent) ? Math.min(100, Math.max(0, percent)) : 0),
  };
  for (const listener of record.listeners) listener(record.state);
};

const subscribeProgress = (user, requestId, listener) => {
  const record = progressRecord(user, requestId);
  if (record.listeners.size >= 3) throw Object.assign(new Error("Too many progress connections."), { statusCode: 429 });
  record.listeners.add(listener);
  listener(record.state);
  return () => record.listeners.delete(listener);
};

module.exports = { updateProgress, subscribeProgress };
