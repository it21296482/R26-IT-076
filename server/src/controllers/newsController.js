const {
  collectNews
} = require("../services/news/newsCollectorService");

const {
  analyzeNewsArticles
} = require("../services/news/newsAnalysisService");

async function getNews(req, res) {
  try {
    const collected =
      await collectNews();

    const analyzed =
      analyzeNewsArticles(collected);

    const data =
      analyzed.map((article) => ({
        title: article.title,
        description: article.description,
        url: article.url,
        source: article.source,
        publishedAt: article.published_at,

        type: article.newsType,

        companies:
          article.targetCompanies || [],

        marketImpact:
          article.marketImpact,

        sentiment:
          article.sentiment,

        sentimentScore:
          article.sentimentScore,

        confidence:
          article.confidence
      }));

    res.status(200).json({
      success: true,
      count: data.length,
      data
    });

  } catch (error) {
    console.error(
      "Get news failed:",
      error.message
    );

    res.status(500).json({
      success: false,
      message:
        "Failed to fetch financial news"
    });
  }
}

module.exports = {
  getNews
};