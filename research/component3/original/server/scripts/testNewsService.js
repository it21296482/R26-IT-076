require("dotenv").config();

const {
  fetchFinancialNews
} = require("../src/services/news/marketAuxService");

async function test() {
  try {
    console.log(
      "Fetching company-specific news...\n"
    );

    const articles =
      await fetchFinancialNews();

    console.log(
      "\nTotal articles:",
      articles.length
    );

    for (const article of articles) {
      console.log(
        "\n================================"
      );

      console.log(
        "Company:",
        article.targetCompany?.name
      );

      console.log(
        "Title:",
        article.title
      );

      console.log(
        "Published:",
        article.published_at
      );

      console.log(
        "Source:",
        article.source
      );

      console.log(
        "URL:",
        article.url
      );
    }

  } catch (error) {
    console.error(
      "News test failed:",
      error.response?.data || error.message
    );
  }
}

test();