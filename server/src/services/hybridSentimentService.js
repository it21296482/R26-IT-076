const predictSentiment = require("../ml/predictSentiment");
const analyzeRuleBasedSentiment = require("../nlp/ruleBasedSentiment");

async function hybridSentimentAnalysis(text) {
  const mlPrediction = await predictSentiment(text);
  const rulePrediction = analyzeRuleBasedSentiment(text);

  let finalPrediction = mlPrediction;
  let decisionReason = "ml";

  // Strong financial evidence overrides ML
  if (rulePrediction.score >= 2) {
    finalPrediction = "positive";
    decisionReason = "strong-positive-rule";
  } 
  else if (rulePrediction.score <= -2) {
    finalPrediction = "negative";
    decisionReason = "strong-negative-rule";
  }

  // If ML is neutral but financial rules detect sentiment,
  // allow the rule-based system to resolve it.
  else if (
    mlPrediction === "neutral" &&
    rulePrediction.score > 0
  ) {
    finalPrediction = "positive";
    decisionReason = "rule-resolved-neutral";
  }
  else if (
    mlPrediction === "neutral" &&
    rulePrediction.score < 0
  ) {
    finalPrediction = "negative";
    decisionReason = "rule-resolved-neutral";
  }

  return {
    mlPrediction,
    rulePrediction,
    finalPrediction,
    decisionReason
  };
}

module.exports = hybridSentimentAnalysis;