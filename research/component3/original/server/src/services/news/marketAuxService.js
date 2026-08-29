const axios = require("axios");
const COMPANIES = require("../../config/companies");

const BASE_URL = "https://api.marketaux.com/v1/news/all";

// --------------------------------------------------
// Normalize text
// --------------------------------------------------

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// --------------------------------------------------
// Check whether article is relevant to company
// --------------------------------------------------

function isRelevantArticle(article, company) {
  const text = normalize(
    `${article.title || ""} ${article.description || ""}`
  );

  return company.searchTerms.some((term) => {
    const normalizedTerm = normalize(term);

    // Short aliases such as NTB, JKH, BIL
    // must appear as complete words
    if (normalizedTerm.length <= 3) {
      const words = text.split(" ");
      return words.includes(normalizedTerm);
    }

    // Longer company names
    return text.includes(normalizedTerm);
  });
}

// --------------------------------------------------
// Fetch news for ONE company
// --------------------------------------------------

async function fetchCompanyNews(company, maxPages = 5) {
  const apiKey = process.env.MARKETAUX_API_KEY;

  if (!apiKey) {
    throw new Error(
      "MARKETAUX_API_KEY is missing from .env"
    );
  }

  // Last 180 days only
  const publishedAfter = new Date();

  publishedAfter.setDate(
    publishedAfter.getDate() - 180
  );

  const publishedAfterFormatted =
    publishedAfter
      .toISOString()
      .split(".")[0];

  const articles = [];

  for (let page = 1; page <= maxPages; page++) {
    const params = {
      api_token: apiKey,
      language: "en",
      limit: 3,
      page,
      group_similar: true,
      published_after: publishedAfterFormatted
    };

    // Use MarketAux symbol when available
    if (company.symbol) {
      params.symbols = company.symbol;
      params.filter_entities = true;
    } else {
      // Keyword search for companies without symbol
      params.search =
        company.searchTerms.join(" OR ");
    }

    const response = await axios.get(
      BASE_URL,
      { params }
    );

    const pageArticles =
      response.data.data || [];

    if (pageArticles.length === 0) {
      break;
    }

    for (const article of pageArticles) {
      // Reject incorrectly associated articles
      if (!isRelevantArticle(article, company)) {
        continue;
      }

      articles.push({
        ...article,

        targetCompany: {
          key: company.key,
          name: company.name,
          symbol: company.symbol
        },

        newsProvider: "marketaux"
      });
    }

    // If fewer than 3 returned,
    // there probably isn't another page
    if (pageArticles.length < 3) {
      break;
    }
  }

  return articles;
}

// --------------------------------------------------
// Fetch news for ALL configured companies
// --------------------------------------------------

async function fetchFinancialNews() {
  try {
    const allArticles = [];

    for (const company of COMPANIES) {
      console.log(
        `Fetching MarketAux news for ${company.name}...`
      );

      try {
        const articles =
          await fetchCompanyNews(
            company,
            5
          );

        console.log(
          `${company.name}: ${articles.length} relevant article(s)`
        );

        allArticles.push(...articles);

      } catch (error) {
        console.error(
          `Failed to fetch ${company.name}:`,
          error.response?.data ||
            error.message
        );
      }
    }

    // Remove duplicate URLs
    const uniqueArticles = Array.from(
      new Map(
        allArticles.map((article) => [
          article.url,
          article
        ])
      ).values()
    );

    // Sort newest first
    uniqueArticles.sort(
      (a, b) =>
        new Date(b.published_at) -
        new Date(a.published_at)
    );

    console.log(
      `Total unique MarketAux articles: ${uniqueArticles.length}`
    );

    return uniqueArticles;

  } catch (error) {
    console.error(
      "MarketAux service error:",
      error.response?.data ||
        error.message
    );

    throw error;
  }
}

module.exports = {
  fetchFinancialNews,
  fetchCompanyNews,
  isRelevantArticle,
  COMPANIES
};