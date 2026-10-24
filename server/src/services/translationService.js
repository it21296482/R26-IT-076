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
const waitingRequests = [];
const enqueue = (task) => new Promise((resolve, reject) => {
  if (waitingRequests.length >= 24) { reject(new Error("Translation queue is busy")); return; }
  const run = () => {
    activeRequests++;
    Promise.resolve().then(task).then(resolve, reject).finally(() => {
      activeRequests--;
      waitingRequests.shift()?.();
    });
  };
  if (activeRequests < 2) run(); else waitingRequests.push(run);
});

// Translate presentation copy only, never model data, identifiers, or source quotes.
const DISPLAY_KEYS = new Set([
  "headline", "plain_language_overview", "potential", "key_risks",
  "what_could_change_the_picture", "uncertainty", "non_advisory_note",
  "market_outlook", "company_report_takeaway", "external_context", "risk_outlook",
  "summary", "key_strengths", "key_concerns", "supporting_evidence",
  "risk_evidence", "plain_conclusion", "label", "narrative", "explanation",
  "plain_explanation", "meaning", "businessChannel", "ifFactorRises",
  "ifFactorFalls", "contributionEstimate", "interpretation", "message",
  "plain_assessment", "limitations", "top_drivers", "market_comparison",
  "conditional_upside", "evidence_used", "why_no_anomaly", "recovery_outlook",
  "if_disruption_persists", "company_exposure", "conditions", "range_note",
  "evidence_status", "anomaly_context", "scenario_note", "caution", "horizon",
  "statisticalReading",
]);

const runTranslation = async (texts, language, names = []) => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "cse-translation-"));
  try {
    const input = path.join(directory, "input.json");
    await fs.writeFile(input, JSON.stringify({ language, texts, names }), { mode: 0o600 });
    const defaultPython = process.platform === "win32" ? "python" : "python3";
    const { stdout } = await execute(process.env.PYTHON_BIN || defaultPython, [SCRIPT, "--input", input], {
      cwd: path.resolve(__dirname, "../../../component_2"),
      env: process.env, timeout: 240000, maxBuffer: 2 * 1024 * 1024,
    });
    const output = JSON.parse(String(stdout).trim().split(/\r?\n/).at(-1));
    if (!output.translations || typeof output.translations !== "object") throw new Error("Translation unavailable");
    return output;
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
};

const protectedTokens = (text) => text.match(/\b(?:LKR|USD|EUR|GBP|JPY|INR)\s+[+-]?\d[\d,.]*(?:%|\b)|\b[A-Z0-9]{2,12}\.[NX]\d{4}\b|\b(?:LKR|USD|EUR|GBP|JPY|INR|ASPI|VIX|JKH|BIL)\b|[+-]?\d[\d,.]*(?:%|\b)/g) || [];
const validTranslation = (original, translated, language, names = []) => {
  if (typeof translated !== "string" || !translated.trim() || translated.length > original.length * 8 + 200) return false;
  const script = language === "si" ? /[\u0D80-\u0DFF]/ : /[\u0B80-\u0BFF]/;
  return script.test(translated)
    && names.every((name) => !name || !original.includes(name) || translated.includes(name))
    && JSON.stringify(protectedTokens(original).sort()) === JSON.stringify(protectedTokens(translated).sort());
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
  collect(outputs.market?.estimate_quality);
  collect(outputs.market?.deviation_history);
  collect(outputs.market?.limitations, true);
  for (const context of [outputs.newsSentiment, outputs.marketRiskContext, outputs.externalContext]) {
    collect(context?.externalFactors?.factors);
    collect(context?.externalFactors?.marketComparison);
    // The result page shows six headlines. Hidden source items stay verbatim.
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
    if (!request) {
      request = enqueue(async () => {
        const output = {}, groups = [];
        let failureCode = null;
        let group = [], size = 0;
        missing.forEach((text, index) => {
          const localTranslation = process.env.TRANSLATION_PROVIDER === "nllb" || (process.env.LLM_PROVIDER === "ollama" && !process.env.TRANSLATION_PROVIDER);
          if (group.length && (size + text.length > (localTranslation ? 20000 : 4000) || group.length >= (localTranslation ? 64 : 8))) {
            groups.push(group); group = []; size = 0;
          }
          group.push({ text, index }); size += text.length;
        });
        if (group.length) groups.push(group);
        for (const batch of groups) {
          let response;
          try {
            response = await translateBatch(batch.map((entry) => entry.text), targetLanguage, [result.companyName, result.stockSymbol].filter(Boolean));
          } catch {
            return { translations: output, failureCode: "TRANSLATION_PROVIDER_UNAVAILABLE" };
          }
          const values = response.translations || response;
          batch.forEach((entry, index) => { output[String(entry.index)] = values[String(index)]; });
          failureCode ||= response.failureCode;
          // A rejected sentence must not prevent unrelated explanations translating.
          if (response.failureCode && response.failureCode !== "TRANSLATION_VALIDATION_FAILED" && !Object.keys(values).length) break;
        }
        return { translations: output, failureCode };
      });
      pending.set(key, request);
      request.finally(() => pending.delete(key)).catch(() => {});
    }
    try {
      const response = await request;
      result.localizationFailure = response.failureCode || null;
      const translated = response.translations;
      missing.forEach((text, index) => {
        const value = translated[String(index)];
        if (!validTranslation(text, value, targetLanguage, [result.companyName, result.stockSymbol])) return;
        translations.set(text, value);
        if (cache.size >= 2000) cache.delete(cache.keys().next().value);
        cache.set(`${targetLanguage}:${text}`, { value, expires: now + CACHE_TTL });
      });
    } catch {
      result.localizationFailure = "TRANSLATION_PROVIDER_UNAVAILABLE";
      // An outage must not erase financial evidence or expose raw credential errors.
    }
  }
  for (const entry of entries) entry.object[entry.key] = translations.get(entry.text) || entry.text;
  const translatedCount = texts.filter((text) => translations.has(text)).length;
  result.localization = {
    requestedLanguage: targetLanguage,
    status: translatedCount === texts.length ? "completed" : translatedCount ? "partial" : "unavailable",
    translatedCount, totalCount: texts.length, machineTranslated: translatedCount > 0,
    failureCode: result.localizationFailure || null,
  };
  delete result.localizationFailure;
  return result;
};

module.exports = { SUPPORTED_LANGUAGES, translateAnalysis, validTranslation, protectedTokens };
