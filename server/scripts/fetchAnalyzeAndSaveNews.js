require("dotenv").config();

const mongoose = require("mongoose");

const {
  fetchAndAnalyzeNews
} = require("../src/services/newsAnalysisService");

const {
  saveAnalyzedNews
} = require("../src/services/newsStorageService");

async function run() {
  try {
    await mongoose.connect(process.env.MONGODB_URI);

    console.log("MongoDB connected ✅");

    const articles =
      await fetchAndAnalyzeNews();

    console.log(
      "Articles analyzed:",
      articles.length
    );

    const saved =
      await saveAnalyzedNews(articles);

    console.log(
      "New articles saved:",
      saved.length
    );

    saved.forEach((article) => {
      console.log(
        article.title,
        "→",
        article.sentiment.finalPrediction
      );
    });

  } catch (error) {
    console.error(
      "Pipeline failed:",
      error.message
    );
  } finally {
    await mongoose.disconnect();
  }
}

run();