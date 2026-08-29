require("dotenv").config();

const {
  collectNews
} = require(
  "../src/services/news/newsCollectorService"
);

const {
  analyzeNewsArticles
} = require(
  "../src/services/news/newsAnalysisService"
);

async function test() {
  try {
    const articles =
      await collectNews();

    const analyzed =
      analyzeNewsArticles(
        articles
      );

    console.log(
      "\nAnalyzed articles:",
      analyzed.length
    );

    for (const article of analyzed) {
      console.log(
        "\n============================"
      );

      console.log(
        "Title:",
        article.title
      );

      console.log(
        "Sentiment:",
        article.sentiment
      );

      console.log(
        "Score:",
        article.sentimentScore
      );

      console.log(
        "Confidence:",
        article.confidence
      );

      console.log(
        "Companies:",
        article.targetCompanies
      );

      console.log(
        "Text:",
        article.analysisText.slice(
          0,
          200
        )
      );
    }
  } catch (error) {
    console.error(
      "News analysis test failed:",
      error.message
    );
  }
}

test();