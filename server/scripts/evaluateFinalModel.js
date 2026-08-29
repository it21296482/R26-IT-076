const evaluateModel = require("../src/ml/evaluateModel");
const predictSentiment = require("../src/ml/predictSentiment");
const hybridSentimentAnalysis =
  require("../src/services/hybridSentimentService");

const finalTestData =
  require("../data/evaluation/final_test");

async function runFinalEvaluation() {
  console.log("\n===== FINAL UNSEEN TEST =====");

  console.log("\n===== NAIVE BAYES =====");

  const mlResults = await evaluateModel(
    finalTestData,
    predictSentiment
  );

  printResults(mlResults);

  console.log("\n===== HYBRID MODEL =====");

  const hybridResults = await evaluateModel(
    finalTestData,
    async (text) => {
      const result =
        await hybridSentimentAnalysis(text);

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
    "Correct:",
    results.correct,
    "/",
    results.total
  );

  console.log(
    "Macro F1:",
    results.macroF1.toFixed(3)
  );

  console.log("\nConfusion Matrix:");
  console.table(results.confusionMatrix);

  console.log("\nPer-Class Metrics:");

  for (const [label, metrics] of Object.entries(
    results.metrics
  )) {
    console.log(label.toUpperCase());

    console.log(
      " Precision:",
      metrics.precision.toFixed(3)
    );

    console.log(
      " Recall:",
      metrics.recall.toFixed(3)
    );

    console.log(
      " F1:",
      metrics.f1.toFixed(3)
    );
  }
}

runFinalEvaluation().catch(console.error);