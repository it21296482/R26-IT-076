const axios = require("axios");

const SUPPORTED_LANGUAGES = new Set(["en", "si", "ta"]);
const translationCache = new Map();

const shouldTranslate = (value) => (
  typeof value === "string" &&
  value.trim() &&
  /[A-Za-z]/.test(value) &&
  !/^https?:\/\//i.test(value)
);

const translateText = async (text, targetLanguage) => {
  if (targetLanguage === "en" || !shouldTranslate(text)) return text;
  if (text.length > 450) {
    const words = text.split(/(\s+)/);
    const chunks = [];
    let current = "";
    words.forEach((word) => {
      if (current.length + word.length > 450 && current.trim()) {
        chunks.push(current);
        current = "";
      }
      current += word;
    });
    if (current) chunks.push(current);
    return (await Promise.all(chunks.map((chunk) => translateText(chunk, targetLanguage)))).join("");
  }

  const cacheKey = `${targetLanguage}:${text}`;
  if (translationCache.has(cacheKey)) return translationCache.get(cacheKey);

  try {
    const response = await axios.get("https://api.mymemory.translated.net/get", {
      params: { q: text, langpair: `en|${targetLanguage}` },
      timeout: 10000,
    });
    const translated = response.data?.responseData?.translatedText?.trim();
    const result = translated || text;
    translationCache.set(cacheKey, result);
    return result;
  } catch {
    // Translation is an enhancement; never make a completed analysis unavailable.
    return text;
  }
};

const translateValue = async (value, targetLanguage) => {
  if (targetLanguage === "en" || value === null || value === undefined) return value;
  if (typeof value === "string") return translateText(value, targetLanguage);
  if (Array.isArray(value)) return Promise.all(value.map((item) => translateValue(item, targetLanguage)));
  if (typeof value !== "object") return value;

  const entries = await Promise.all(
    Object.entries(value).map(async ([key, item]) => [key, await translateValue(item, targetLanguage)])
  );
  return Object.fromEntries(entries);
};

const translateAnalysis = async (analysis, language) => {
  const targetLanguage = SUPPORTED_LANGUAGES.has(language) ? language : "en";
  if (targetLanguage === "en") return analysis;
  return translateValue(analysis, targetLanguage);
};

module.exports = { SUPPORTED_LANGUAGES, translateAnalysis };
