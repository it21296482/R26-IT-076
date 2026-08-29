const path = require("path");
const trainModel = require("../src/ml/trainModel");

console.log("Starting sentiment model training...");

const classifier = trainModel();

const modelPath = path.join(
  __dirname,
  "../models/sentimentModel.json"
);

classifier.save(modelPath, (err) => {
  if (err) {
    console.error("Error saving model:", err);
    return;
  }

  console.log("Sentiment model trained successfully!");
  console.log("Model saved to:", modelPath);
});