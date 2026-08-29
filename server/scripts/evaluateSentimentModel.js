const evaluateModel = require("../src/ml/evaluateModel");
const predictSentiment = require("../src/ml/predictSentiment");
const hybridSentimentAnalysis =
  require("../src/services/hybridSentimentService");

const testData =
  require("../data/evaluation/sentiment_test");

async function run() {
  console.log("\n===== NAIVE BAYES =====");

  const mlResults = await evaluateModel(
    testData,
    predictSentiment
  );

  printResults(mlResults);

  console.log("\n===== HYBRID MODEL =====");

  const hybridResults = await evaluateModel(
    testData,
    async (text) => {
      const result = await hybridSentimentAnalysis(text);
      return result.finalPrediction;
    }
  );

  printResults(hybridResults);
}

function printResults(results) {
  console.log(
    "Accuracy:",
    results.accuracy.toFixed(2) + "%"
  );

  console.log(
    "Macro F1:",
    results.macroF1.toFixed(3)
  );

  console.log("\nConfusion Matrix:");
  console.table(results.confusionMatrix);

  console.log("\nPer-Class Metrics:");

  for (const [label, values] of Object.entries(results.metrics)) {
    console.log(label.toUpperCase());

    console.log(
      " Precision:",
      values.precision.toFixed(3)
    );

    console.log(
      " Recall:",
      values.recall.toFixed(3)
    );

    console.log(
      " F1:",
      values.f1.toFixed(3)
    );
  }
}

run().catch(console.error);