const fs = require("fs/promises");
const os = require("os");
const path = require("path");
const { execFile } = require("child_process");
const { promisify } = require("util");
const { createHash } = require("crypto");

const execute = promisify(execFile);
const SUPPORTED_LANGUAGES = new Set(["en", "si", "ta"]);
const cache = new Map();
const pending = new Map();
const SCRIPT = path.resolve(__dirname, "../../../component_2/src/translate_insights.py");
const CACHE_TTL = 30 * 60 * 1000;
let activeRequests = 0;

// Translate presentation copy only, never model data, identifiers, or source quotes.
const DISPLAY_KEYS = new Set([
  "headline", "plain_language_overview", "potential", "key_risks",
  "what_could_change_the_picture", "uncertainty", "non_advisory_note",
  "market_outlook", "company_report_takeaway", "external_context", "risk_outlook",
  "summary", "key_strengths", "key_concerns", "supporting_evidence",
  "risk_evidence", "plain_conclusion", "label", "narrative", "explanation",
  "plain_explanation", "meaning", "businessChannel", "ifFactorRises",
  "ifFactorFalls", "contributionEstimate", "interpretation", "message",
]);

const runTranslation = async (texts, language) => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "cse-translation-"));
  try {
    const input = path.join(directory, "input.json");
    await fs.writeFile(input, JSON.stringify({ language, texts }), { mode: 0o600 });
    const defaultPython = process.platform === "win32" ? "python" : "python3";
    const { stdout } = await execute(process.env.PYTHON_BIN || defaultPython, [SCRIPT, "--input", input], {
      cwd: path.resolve(__dirname, "../../../component_2"),
      env: process.env, timeout: 150000, maxBuffer: 2 * 1024 * 1024,
    });
    const output = JSON.parse(String(stdout).trim().split(/\r?\n/).at(-1));
    if (!output.translations || typeof output.translations !== "object") throw new Error("Translation unavailable");
    return output.translations;
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
};

const protectedTokens = (text) => text.match(/\b[A-Z]{2,10}\.N\d{4}\b|\b(?:LKR|USD|EUR|GBP|JPY|INR|ASPI|VIX|JKH|BIL)\b|[+-]?\d[\d,.]*(?:%|\b)/g) || [];
const validTranslation = (original, translated, language, names = []) => {
  if (typeof translated !== "string" || !translated.trim() || translated.length > original.length * 8 + 200) return false;
  const script = language === "si" ? /[\u0D80-\u0DFF]/ : /[\u0B80-\u0BFF]/;
  return script.test(translated)
    && names.every((name) => !name || !original.includes(name) || translated.includes(name))
    && JSON.stringify(protectedTokens(original)) === JSON.stringify(protectedTokens(translated));
};

const translateAnalysis = async (analysis, language, { translateBatch = runTranslation, now = Date.now() } = {}) => {
  const targetLanguage = SUPPORTED_LANGUAGES.has(language) ? language : "en";
  if (targetLanguage === "en") return analysis;
  const result = JSON.parse(JSON.stringify(analysis));
  const entries = [];
  const collect = (object, inheritedDisplay = false) => {
    if (!object || typeof object !== "object") return;
    for (const [key, value] of Object.entries(object)) {
      const display = Array.isArray(object) ? inheritedDisplay : DISPLAY_KEYS.has(key);
      if (typeof value === "string" && display && /[A-Za-z]/.test(value)
          && !/^[A-Z\d. /%-]+$/.test(value) && !/^https?:\/\//i.test(value)) {
        entries.push({ object, key, text: value });
      } else if (value && typeof value === "object") collect(value, display);
    }
  };
  const outputs = result.outputs || {};
  collect(outputs.unifiedInsight?.insight);
  collect(outputs.report?.insight?.investor_friendly_insight);
  collect(outputs.riskImpact);
  collect(outputs.market?.anomaly);
  collect(outputs.market?.horizons);
  for (const context of [outputs.newsSentiment, outputs.marketRiskContext, outputs.externalContext]) {
    collect(context?.externalFactors?.factors);
    for (const article of (context?.articles || []).slice(0, 6)) {
      if (article.title) entries.push({ object: article, key: "title", text: article.title });
    }
  }
  for (let i = 0; i < (result.warnings || []).length; i++) {
    entries.push({ object: result.warnings, key: i, text: result.warnings[i] });
  }
  const texts = [...new Set(entries.map((entry) => entry.text))];
  const translations = new Map();
  const missing = texts.filter((text) => {
    const cached = cache.get(`${targetLanguage}:${text}`);
    if (cached && cached.expires > now) { translations.set(text, cached.value); return false; }
    return true;
  });

  if (missing.length && JSON.stringify(missing).length <= 150000) {
    const key = createHash("sha256").update(`${targetLanguage}:${JSON.stringify(missing)}`).digest("hex");
    let request = pending.get(key);
    if (!request && activeRequests < 2) {
      activeRequests++;
      request = Promise.resolve().then(() => translateBatch(missing, targetLanguage));
      pending.set(key, request);
      request.finally(() => { activeRequests--; pending.delete(key); }).catch(() => {});
    }
    try {
      const translated = request ? await request : {};
      missing.forEach((text, index) => {
        const value = translated[String(index)];
        if (!validTranslation(text, value, targetLanguage, [result.companyName, result.stockSymbol])) return;
        translations.set(text, value);
        if (cache.size >= 2000) cache.delete(cache.keys().next().value);
        cache.set(`${targetLanguage}:${text}`, { value, expires: now + CACHE_TTL });
      });
    } catch {
      // An outage must not erase financial evidence or expose raw credential errors.
    }
  }
  for (const entry of entries) entry.object[entry.key] = translations.get(entry.text) || entry.text;
  const translatedCount = texts.filter((text) => translations.has(text)).length;
  result.localization = {
    requestedLanguage: targetLanguage,
    status: translatedCount === texts.length ? "completed" : translatedCount ? "partial" : "unavailable",
    translatedCount, totalCount: texts.length, machineTranslated: translatedCount > 0,
  };
  return result;
};

module.exports = { SUPPORTED_LANGUAGES, translateAnalysis, validTranslation };
