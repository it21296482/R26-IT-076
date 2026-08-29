const natural = require("natural");
const path = require("path");
const preprocess = require("../nlp/preprocess");

const modelPath = path.join(
  __dirname,
  "../../models/sentimentModel.json"
);

function predictSentiment(text) {
  return new Promise((resolve, reject) => {
    natural.BayesClassifier.load(modelPath, null, (err, classifier) => {
      if (err) {
        return reject(err);
      }

      const cleaned = preprocess(text);
      const prediction = classifier.classify(cleaned);

      resolve(prediction);
    });
  });
}

module.exports = predictSentiment;