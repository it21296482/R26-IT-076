const financialLexicon = require("./financialLexicon");

// Rule-based normalization:
// intentionally NO stemming
function normalizeForRules(text) {
  if (!text || typeof text !== "string") {
    return "";
  }

  return text
    .toLowerCase()
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function analyzeRuleBasedSentiment(text) {
  const cleanedText = normalizeForRules(text);

  let workingText = ` ${cleanedText} `;

  let score = 0;

  const positiveMatches = [];
  const negativeMatches = [];
  const neutralMatches = [];

  // ----------------------------------
  // 1. MATCH PHRASES FIRST
  // ----------------------------------

  for (const [phrase, weight] of Object.entries(
    financialLexicon.positive.phrases || {}
  )) {
    const normalizedPhrase = normalizeForRules(phrase);

    const searchValue = ` ${normalizedPhrase} `;

    if (workingText.includes(searchValue)) {
      score += weight;

      positiveMatches.push({
        term: phrase,
        weight
      });

      // Remove phrase so its individual words
      // are not counted again.
      workingText = workingText.replace(searchValue, " ");
    }
  }

  for (const [phrase, weight] of Object.entries(
    financialLexicon.negative.phrases || {}
  )) {
    const normalizedPhrase = normalizeForRules(phrase);

    const searchValue = ` ${normalizedPhrase} `;

    if (workingText.includes(searchValue)) {
      score += weight;

      negativeMatches.push({
        term: phrase,
        weight
      });

      workingText = workingText.replace(searchValue, " ");
    }
  }

  // ----------------------------------
  // 2. MATCH REMAINING SINGLE WORDS
  // ----------------------------------

  const remainingWords = workingText
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  for (const word of remainingWords) {
    if (
      Object.prototype.hasOwnProperty.call(
        financialLexicon.positive,
        word
      ) &&
      word !== "phrases"
    ) {
      const weight = financialLexicon.positive[word];

      score += weight;

      if (weight !== 0) {
        positiveMatches.push({
          term: word,
          weight
        });
      }
    }

    if (
      Object.prototype.hasOwnProperty.call(
        financialLexicon.negative,
        word
      ) &&
      word !== "phrases"
    ) {
      const weight = financialLexicon.negative[word];

      score += weight;

      if (weight !== 0) {
        negativeMatches.push({
          term: word,
          weight
        });
      }
    }
  }

  // ----------------------------------
  // 3. NEUTRAL PHRASES
  // ----------------------------------

  for (const phrase of financialLexicon.neutralPhrases || []) {
    const normalizedPhrase = normalizeForRules(phrase);

    if (cleanedText.includes(normalizedPhrase)) {
      neutralMatches.push(phrase);
    }
  }

  // ----------------------------------
  // 4. FINAL LABEL
  // ----------------------------------

  let label = "neutral";

  if (score > 0) {
    label = "positive";
  } else if (score < 0) {
    label = "negative";
  }

  return {
    label,
    score,
    positiveMatches,
    negativeMatches,
    neutralMatches
  };
}

module.exports = analyzeRuleBasedSentiment;