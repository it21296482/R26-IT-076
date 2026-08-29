const predictSentiment = require("../src/ml/predictSentiment");

async function test() {
  const news = [
    "JKH reports record profits this quarter.",
    "Colombo stock market falls amid uncertainty.",
    "Central Bank announces monetary policy."
  ];

  for (const article of news) {
    const prediction = await predictSentiment(article);

    console.log("--------------------------------");
    console.log("News:", article);
    console.log("Prediction:", prediction);
  }
}

test();