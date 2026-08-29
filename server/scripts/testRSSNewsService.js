require("dotenv").config();

const {
  fetchRSSNews
} = require("../src/services/news/rssNewsService");

async function test() {
  try {
    console.log("Fetching RSS news...\n");

    const articles = await fetchRSSNews();

    console.log(
      "\nTotal relevant RSS articles:",
      articles.length
    );

    for (const article of articles) {
      console.log("\n============================");

      console.log("Title:", article.title);
      console.log("Source:", article.source);
      console.log("Published:", article.published_at);
      console.log("Companies:", article.targetCompanies);
      console.log("Market impact:", article.marketImpact);
      console.log("URL:", article.url);
    }
  } catch (error) {
    console.error(
      "RSS test failed:",
      error.message
    );
  }
}

test();