const News = require("../models/News");

async function saveAnalyzedNews(articles) {
  const savedArticles = [];

  for (const article of articles) {
    try {
      // Avoid saving duplicate articles
      const existing = await News.findOne({
        url: article.url
      });

      if (existing) {
        console.log(
          "Skipping duplicate:",
          article.title
        );

        continue;
      }

      const news = await News.create({
        title: article.title,
        description: article.description,
        source: article.source,
        url: article.url,
        publishedAt: article.publishedAt,
        entities: article.entities,
        sentiment: article.sentiment
      });

      savedArticles.push(news);

    } catch (error) {
      console.error(
        "Failed to save:",
        article.title,
        error.message
      );
    }
  }

  return savedArticles;
}

module.exports = {
  saveAnalyzedNews
};