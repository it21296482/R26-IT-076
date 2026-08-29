async function evaluateModel(testData, predictor) {
  const labels = ["positive", "negative", "neutral"];

  const confusionMatrix = {
    positive: { positive: 0, negative: 0, neutral: 0 },
    negative: { positive: 0, negative: 0, neutral: 0 },
    neutral: { positive: 0, negative: 0, neutral: 0 }
  };

  const predictions = [];
  let correct = 0;

  for (const item of testData) {
    const predicted = await predictor(item.text);

    confusionMatrix[item.label][predicted]++;

    if (predicted === item.label) {
      correct++;
    }

    predictions.push({
      text: item.text,
      actual: item.label,
      predicted
    });
  }

  const metrics = {};

  for (const label of labels) {
    const TP = confusionMatrix[label][label];

    let FP = 0;
    let FN = 0;

    for (const other of labels) {
      if (other !== label) {
        FP += confusionMatrix[other][label];
        FN += confusionMatrix[label][other];
      }
    }

    const precision = TP + FP === 0 ? 0 : TP / (TP + FP);
    const recall = TP + FN === 0 ? 0 : TP / (TP + FN);

    const f1 =
      precision + recall === 0
        ? 0
        : (2 * precision * recall) / (precision + recall);

    metrics[label] = {
      precision,
      recall,
      f1
    };
  }

  const macroF1 =
    labels.reduce((sum, label) => sum + metrics[label].f1, 0) /
    labels.length;

  return {
    accuracy: (correct / testData.length) * 100,
    correct,
    total: testData.length,
    confusionMatrix,
    metrics,
    macroF1,
    predictions
  };
}

module.exports = evaluateModel;