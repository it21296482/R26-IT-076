const DIRECTORY_URL = "https://www.cse.lk/api/alphabetical";

const fetchCompanyLetter = async (letter) => {
  const response = await fetch(DIRECTORY_URL, {
    method: "POST", body: new URLSearchParams({ alphabet: letter }),
    headers: { "Content-Type": "application/x-www-form-urlencoded" }, signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new Error(`CSE company directory returned HTTP ${response.status}.`);
  const payload = await response.json();
  if (!Array.isArray(payload.reqAlphabetical)) throw new Error("Unexpected CSE company-directory response.");
  return payload.reqAlphabetical;
};

const companyName = (value) => String(value || "").toLowerCase()
  .replace(/\b\w/g, (character) => character.toUpperCase()).replace(/\bPlc\b/g, "PLC");

const createDirectoryLoader = ({ fetchLetter = fetchCompanyLetter, now = () => Date.now(), ttlMs = 3600000 } = {}) => {
  let cached = null, expiresAt = 0, pending = null;
  return async () => {
    if (cached && now() < expiresAt) return cached;
    if (pending) return pending;
    pending = (async () => {
      const letters = [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"];
      const found = new Map(), failedLetters = [];
      let index = 0;
      // Bound upstream requests and share the result across concurrent page loads.
      const worker = async () => {
        while (index < letters.length) {
          const letter = letters[index++];
          try {
            for (const row of await fetchLetter(letter)) {
              const symbol = String(row.symbol || "").toUpperCase();
              if (/^[A-Z0-9]+\.[NX][0-9]{4}$/.test(symbol) && row.name) {
                found.set(symbol, { symbol, companyName: companyName(row.name), securityId: row.id });
              }
            }
          } catch { failedLetters.push(letter); }
        }
      };
      await Promise.all(Array.from({ length: 4 }, worker));
      if (!found.size && !cached) throw new Error("The CSE company directory is temporarily unavailable.");
      if (failedLetters.length && cached) {
        for (const row of cached.companies) if (!found.has(row.symbol)) found.set(row.symbol, row);
      }
      cached = { companies: [...found.values()].sort((a, b) => a.companyName.localeCompare(b.companyName) || a.symbol.localeCompare(b.symbol)),
        source: DIRECTORY_URL, fetchedAt: new Date(now()).toISOString(), complete: failedLetters.length === 0,
        failedLetters: failedLetters.sort() };
      expiresAt = now() + (failedLetters.length ? 60000 : ttlMs);
      return cached;
    })();
    try { return await pending; } finally { pending = null; }
  };
};

const fetchCompanyDirectory = createDirectoryLoader();

const mergeCompanyUniverse = (companies, summaries, coveredSymbols, availability) => {
  const stored = new Map(summaries.map((row) => [row.symbol, row]));
  const all = new Map(companies.map((row) => [row.symbol, row]));
  for (const row of summaries) if (!all.has(row.symbol)) all.set(row.symbol, row);
  return [...all.values()].map((company) => {
    const summary = stored.get(company.symbol);
    const stock = { ...company, ...summary, companyName: company.companyName,
      recordCount: summary?.recordCount || 0, validHistoryCount: summary?.validHistoryCount || 0 };
    return { ...stock, ...availability(stock, coveredSymbols), analysisEligible: companies.some((row) => row.symbol === company.symbol) };
  }).sort((a, b) => a.companyName.localeCompare(b.companyName) || a.symbol.localeCompare(b.symbol));
};

module.exports = { createDirectoryLoader, fetchCompanyDirectory, mergeCompanyUniverse };
