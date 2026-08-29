require("dotenv").config();

const {
  fetchWebNews
} = require("../src/services/news/webNewsService");

async function test() {
  try {
    console.log("Fetching web news...\n");

    const articles = await fetchWebNews();

    console.log(
      "\nTotal relevant web articles:",
      articles.length
    );

    for (const article of articles) {
      console.log(
        "\n================================"
      );

      console.log(
        "Type:",
        article.newsType
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
        "Companies:",
        article.targetCompanies
      );

      console.log(
        "Market impact:",
        article.marketImpact
      );

      console.log(
        "Description:",
        article.description
          ? article.description.slice(0, 300)
          : "No description extracted"
      );

      console.log(
        "URL:",
        article.url
      );
    }

  } catch (error) {
    console.error(
      "Web news test failed:",
      error.message
    );
  }
}

test();