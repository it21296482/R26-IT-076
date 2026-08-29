const financialLexicon = require("./financialLexicon");

function extractFeatures(text) {
    const words = text.split(" ");

    let positiveCount = 0;
    let negativeCount = 0;

    words.forEach((word) => {
        if (financialLexicon.positive.includes(word)) {
            positiveCount++;
        }

        if (financialLexicon.negative.includes(word)) {
            negativeCount++;
        }
    });

    return {
        totalWords: words.length,
        positiveWords: positiveCount,
        negativeWords: negativeCount,
        sentimentScore: positiveCount - negativeCount
    };
}

module.exports = extractFeatures;