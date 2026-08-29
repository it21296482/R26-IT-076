const hybridSentimentAnalysis = require("../src/services/hybridSentimentService");

async function run() {

    const samples = [

        "JKH reports record profits this quarter.",

        "Colombo stock market falls amid uncertainty.",

        "Central Bank announces monetary policy."

    ];

    for (const news of samples) {

        const result = await hybridSentimentAnalysis(news);

        console.log("-----------------------------------");
        console.log("News:", news);
        console.log(result);

    }

}

run();