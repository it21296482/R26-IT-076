// Load the trained Naive Bayes classifier
let naiveBayesModel = null;

try {
  naiveBayesModel =
    require("../../ml/trainBayesClassifier");
} catch (error) {
  console.warn(
    "Naive Bayes model not loaded - using rule-based fallback."
  );
}

// Positive financial words
const POSITIVE_WORDS = [
  "profit",
  "profits",
  "growth",
  "rise",
  "rises",
  "rose",
  "higher",
  "gain",
  "gains",
  "gained",
  "increase",
  "increased",
  "improve",
  "improved",
  "strong",
  "stable",
  "upgrade",
  "upgraded",
  "expansion",
  "investment",
  "record",
  "surge",
  "recovery",
  "boost",
  "boosted",
  "positive",
  "up",
  "bullish"
];

// Negative financial words
const NEGATIVE_WORDS = [
  "loss",
  "losses",
  "decline",
  "declined",
  "fall",
  "falls",
  "fell",
  "lower",
  "drop",
  "drops",
  "dropped",
  "decrease",
  "decreased",
  "weak",
  "downgrade",
  "downgraded",
  "debt",
  "inflation",
  "crisis",
  "risk",
  "risks",
  "war",
  "sanctions",
  "volatile",
  "slump",
  "negative",
  "down",
  "dip",
  "dips",
  "dipped",
  "bearish",
  "jitters"
];

// Strong positive financial phrases
const POSITIVE_PHRASES = [
  "profit rises",
  "profit rose",
  "profit jumps",
  "profit jumped",
  "profits rise",
  "revenue rises",
  "revenue grows",
  "earnings increase",
  "earnings rise",
  "stocks close higher",
  "stocks rise",
  "stocks up",
  "shares gain",
  "share price rises",
  "aspi rises",
  "aspi gains",
  "stable outlook",
  "rating affirmed",
  "rating upgraded",
  "foreign investment rises",
  "tourism surge",
  "record profit",
  "economic growth",
  "investment growth"
];

// Strong negative financial phrases
const NEGATIVE_PHRASES = [
  "stocks close down",
  "stocks close lower",
  "stocks drop",
  "stocks dip",
  "stocks trend down",
  "stocks edge down",
  "aspi dips",
  "aspi drops",
  "aspi down",
  "market declines",
  "market falls",
  "profit falls",
  "profit drops",
  "loss widens",
  "revenue down",
  "revenue falls",
  "tourism revenue down",
  "inflation rises",
  "inflation increases",
  "credit downgrade",
  "rating downgraded",
  "global jitters",
  "profit taking"
];

// Normalize text
function normalizeText(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Keep score between -1 and 1
function clampScore(score) {
  return Math.max(
    -1,
    Math.min(1, score)
  );
}

// Calculate rule-based score
function calculateRuleScore(text) {
  const normalized =
    normalizeText(text);

  const words =
    normalized.split(" ");

  let positiveCount = 0;
  let negativeCount = 0;
  let positivePhraseCount = 0;
  let negativePhraseCount = 0;

  // Count individual words
  for (const word of words) {
    if (
      POSITIVE_WORDS.includes(word)
    ) {
      positiveCount++;
    }

    if (
      NEGATIVE_WORDS.includes(word)
    ) {
      negativeCount++;
    }
  }

  // Count positive phrases
  for (
    const phrase of
      POSITIVE_PHRASES
  ) {
    if (
      normalized.includes(
        normalizeText(phrase)
      )
    ) {
      positivePhraseCount++;
    }
  }

  // Count negative phrases
  for (
    const phrase of
      NEGATIVE_PHRASES
  ) {
    if (
      normalized.includes(
        normalizeText(phrase)
      )
    ) {
      negativePhraseCount++;
    }
  }

  // Words have weight 1 and phrases have weight 2
  const rawScore =
  positiveCount -
  negativeCount +
  positivePhraseCount * 2 -
  negativePhraseCount * 2;

const totalWeight =
  positiveCount +
  negativeCount +
  positivePhraseCount * 2 +
  negativePhraseCount * 2;

  if (totalWeight === 0) {
    return {
      score: 0,
      positiveCount,
      negativeCount,
      positivePhraseCount,
      negativePhraseCount
    };
  }

  return {
    score:
      clampScore(
        rawScore /
        totalWeight
      ),

    positiveCount,
    negativeCount,
    positivePhraseCount,
    negativePhraseCount
  };
}

// Convert score into label
function getSentimentLabel(score) {
  if (score >= 0.2) {
    return "positive";
  }

  if (score <= -0.2) {
    return "negative";
  }

  return "neutral";
}

// Convert ML label into numeric score
function predictionToScore(label) {
  const value =
    String(label || "")
      .toLowerCase();

  if (value === "positive") {
    return 1;
  }

  if (value === "negative") {
    return -1;
  }

  return 0;
}

// Run trained Naive Bayes classifier
function getMLPrediction(text) {
  if (
    !naiveBayesModel ||
    typeof naiveBayesModel.classify !==
      "function"
  ) {
    return {
      label: "neutral",
      score: 0,
      confidence: 0,
      available: false
    };
  }

  try {
    const label =
      naiveBayesModel.classify(
        text
      );

    const classifications =
      naiveBayesModel
        .getClassifications(text);

    const bestResult =
      classifications.find(
        (item) =>
          item.label === label
      );

    const total =
      classifications.reduce(
        (sum, item) =>
          sum +
          Number(
            item.value || 0
          ),
        0
      );

    const confidence =
      bestResult &&
      total > 0
        ? Number(
            bestResult.value
          ) / total
        : 0;

    return {
      label:
        String(
          label || "neutral"
        ).toLowerCase(),

      score:
        predictionToScore(
          label
        ),

      confidence:
        Math.min(
          Math.max(
            confidence,
            0
          ),
          1
        ),

      available: true
    };
  } catch (error) {
    console.warn(
      "Naive Bayes prediction failed:",
      error?.message ||
        error
    );

    return {
      label: "neutral",
      score: 0,
      confidence: 0,
      available: false
    };
  }
}

// Combine ML and rule predictions
function combinePredictions(
  mlResult,
  ruleResult
) {
  const ruleScore =
    ruleResult.score;

  // Strong rule signal overrides ML
  if (ruleScore >= 0.5) {
    return {
      label: "positive",
      score: ruleScore,
      confidence:
        Math.abs(ruleScore),
      decisionReason:
        "financial-rule"
    };
  }

  if (ruleScore <= -0.5) {
    return {
      label: "negative",
      score: ruleScore,
      confidence:
        Math.abs(ruleScore),
      decisionReason:
        "financial-rule"
    };
  }

  // Rule-only fallback
  if (!mlResult.available) {
    return {
      label:
        getSentimentLabel(
          ruleScore
        ),
      score: ruleScore,
      confidence:
        Math.abs(ruleScore),
      decisionReason:
        "rule-only"
    };
  }

  // Ignore weak ML guesses
  if (mlResult.confidence < 0.55) {
    return {
      label:
        getSentimentLabel(
          ruleScore
        ),
      score: ruleScore,
      confidence:
        Math.abs(ruleScore),
      decisionReason:
        "low-ml-confidence"
    };
  }

  // Rules get slightly more importance for financial news
  const mlWeight = 0.4;
  const ruleWeight = 0.6;

  const hybridScore =
    clampScore(
      mlResult.score * mlWeight +
      ruleScore * ruleWeight
    );

  return {
    label:
      getSentimentLabel(
        hybridScore
      ),

    score:
      hybridScore,

    confidence:
      Math.min(
        mlResult.confidence *
          mlWeight +
        Math.abs(ruleScore) *
          ruleWeight,
        1
      ),

    decisionReason:
      "hybrid-ml-rule"
  };
}

// Analyze one article
function analyzeArticle(article) {
  const text =
    article.analysisText ||
    article.title ||
    "";

  const ruleResult =
    calculateRuleScore(
      text
    );

  const mlResult =
    getMLPrediction(
      text
    );

  const finalResult =
    combinePredictions(
      mlResult,
      ruleResult
    );

  return {
    ...article,

    sentiment:
      finalResult.label,

    sentimentScore:
      finalResult.score,

    confidence:
      finalResult.confidence,

    mlPrediction:
      mlResult.label,

    mlScore:
      mlResult.score,

    mlConfidence:
      mlResult.confidence,

    rulePrediction:
      getSentimentLabel(
        ruleResult.score
      ),

    ruleScore:
      ruleResult.score,

    decisionReason:
      finalResult
        .decisionReason,

    sentimentDetails: {
      positiveCount:
        ruleResult
          .positiveCount,

      negativeCount:
        ruleResult
          .negativeCount,

      positivePhraseCount:
        ruleResult
          .positivePhraseCount,

      negativePhraseCount:
        ruleResult
          .negativePhraseCount
    }
  };
}

// Analyze all collected articles
function analyzeNewsArticles(
  articles
) {
  return articles.map(
    analyzeArticle
  );
}

// Export functions
module.exports = {
  analyzeArticle,
  analyzeNewsArticles,
  calculateRuleScore,
  getMLPrediction,
  combinePredictions,
  getSentimentLabel,
  normalizeText
};