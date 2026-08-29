const analyzeRuleBasedSentiment =
  require("../src/nlp/ruleBasedSentiment");

const samples = [
  "JKH reports record profits and strong growth",
  "Company completes capital raise successfully",
  "Bank reports improved margins after cost control",
  "Central Bank announces interest rate hike amid high inflation",
  "Political turmoil increases market uncertainty",
  "Company faces liquidity crisis and rising debt",
  "Board meeting scheduled for next Friday"
];

samples.forEach((text) => {
  console.log("--------------------------------");
  console.log("News:", text);
  console.log(analyzeRuleBasedSentiment(text));
});