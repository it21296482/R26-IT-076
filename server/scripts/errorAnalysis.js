const hybridSentimentAnalysis = require("../src/services/hybridSentimentService");
const testData = require("../data/evaluation/sentiment_test");

async function run() {

    console.log("========== ERROR ANALYSIS ==========\n");

    let errors = [];

    for (const item of testData) {

        const result = await hybridSentimentAnalysis(item.text);

        if (result.finalPrediction !== item.label) {

            errors.push({

                text: item.text,

                actual: item.label,

                predicted: result.finalPrediction,

                ml: result.mlPrediction,

                rule: result.rulePrediction.label,

                score: result.rulePrediction.score

            });

        }

    }

    console.log("Total Errors:", errors.length);

    console.table(errors);

}

run();