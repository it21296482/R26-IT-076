const natural = require("natural");
const stopword = require("stopword");

const tokenizer = new natural.WordTokenizer();
const stemmer = natural.PorterStemmer;

function preprocess(text) {
  if (!text || typeof text !== "string") {
    return "";
  }

  let processed = text.toLowerCase();

  processed = processed.replace(/https?:\/\/\S+/g, "");
  processed = processed.replace(/[0-9]/g, "");
  processed = processed.replace(/[^\w\s]/g, " ");

  let tokens = tokenizer.tokenize(processed);

  tokens = stopword.removeStopwords(tokens);

  tokens = tokens.map((word) => stemmer.stem(word));

  return tokens.join(" ");
}

module.exports = preprocess;