const classifier = require("./bayesClassifier");
const preprocess = require("../nlp/preprocess");

const trainingData = require(
  "../../data/training/sentiment_training_dataset"
);

function trainModel() {
  console.log("Training samples:", trainingData.length);

  trainingData.forEach((item) => {
    const cleaned = preprocess(item.text);

    classifier.addDocument(cleaned, item.label);
  });

  classifier.train();

  return classifier;
}

module.exports = trainModel;