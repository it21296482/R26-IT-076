const createAnalysisQueue = ({ concurrency = 2, maxWaiting = 4 } = {}) => {
  let active = 0;
  const users = new Set(), waiting = [];
  return async (userId, task, onWaiting = () => {}) => {
    const key = String(userId);
    if (users.has(key)) throw Object.assign(new Error("Your previous analysis is still running. Please wait for it to finish."), { statusCode: 409 });
    if (active >= concurrency && waiting.length >= maxWaiting) throw Object.assign(new Error("Analysis is busy. Please try again shortly."), { statusCode: 503 });
    users.add(key);
    try {
      if (active >= concurrency) {
        onWaiting();
        await new Promise((resolve) => waiting.push(resolve));
      } else active += 1;
      try { return await task(); } finally {
        const next = waiting.shift();
        if (next) next(); else active -= 1;
      }
    } finally { users.delete(key); }
  };
};

module.exports = { createAnalysisQueue, runQueuedAnalysis: createAnalysisQueue() };
