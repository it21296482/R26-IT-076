const hybridSentimentAnalysis =
  require("../src/services/hybridSentimentService");

const finalTestData =
  require("../data/evaluation/final_test");

async function run() {
  console.log("===== FINAL TEST ERROR ANALYSIS =====\n");

  const errors = [];

  for (const item of finalTestData) {
    const result = await hybridSentimentAnalysis(item.text);

    if (result.finalPrediction !== item.label) {
      errors.push({
        text: item.text,
        actual: item.label,
        predicted: result.finalPrediction,
        ml: result.mlPrediction,
        rule: result.rulePrediction.label,
        score: result.rulePrediction.score,
        reason: result.decisionReason
      });
    }
  }

  console.log("Total Errors:", errors.length);
  console.table(errors);
}

run().catch(console.error);
