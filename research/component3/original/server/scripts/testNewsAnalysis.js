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

// Test the unified news analysis pipeline
async function test() {
  try {
    console.log(
      "Fetching and analyzing financial news...\n"
    );

    // Collect MarketAux + EconomyNext + NewsFirst articles
    const articles =
      await collectNews();

    // Run sentiment analysis on the collected articles
    const analyzedArticles =
      analyzeNewsArticles(
        articles
      );

    console.log(
      "\nAnalyzed articles:",
      analyzedArticles.length
    );

    for (
      const article of
        analyzedArticles
    ) {
      console.log(
        "\n================================"
      );

      console.log(
        "Title:",
        article.title
      );

      console.log(
        "Source:",
        article.source
      );

      console.log(
        "Published:",
        article.published_at
      );

      console.log(
        "Type:",
        article.newsType
      );

      console.log(
        "Companies:",
        article.targetCompanies
      );

      console.log(
        "Market Impact:",
        article.marketImpact
      );

      console.log(
        "Valid Date:",
        article.hasValidDate
      );

      console.log(
        "Sentiment:",
        article.sentiment
      );

      console.log(
        "Sentiment Score:",
        article.sentimentScore
      );

      console.log(
        "Rule Score:",
        article.ruleScore
      );

      console.log(
        "Confidence:",
        article.confidence
      );

      console.log(
        "Positive Words:",
        article.sentimentDetails
          ?.positiveCount
      );

      console.log(
        "Negative Words:",
        article.sentimentDetails
          ?.negativeCount
      );

      console.log(
        "Analysis Text:",
        article.analysisText?.slice(
          0,
          250
        )
      );
    }
  } catch (error) {
    console.error(
      "News analysis failed:",
      error.response?.data ||
        error.message
    );
  }
}

test();