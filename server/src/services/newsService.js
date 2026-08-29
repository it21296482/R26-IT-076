const axios = require("axios");

const BASE_URL = "https://api.marketaux.com/v1/news/all";

const COMPANIES = [
  {
    key: "browns",
    name: "Browns Investments",
    symbol: "BILN0000.CM",
    search: null
  },
  {
    key: "jkh",
    name: "John Keells Holdings",
    symbol: "JKHN0000.CM",
    search: null
  },
  {
    key: "ndb",
    name: "NDB",
    symbol: null,
    search: '"NDB" OR "NDB Bank" OR "National Development Bank"'
  }
];

async function fetchCompanyNews(company, maxPages = 5) {
  const apiKey = process.env.MARKETAUX_API_KEY;

  if (!apiKey) {
    throw new Error("MARKETAUX_API_KEY is missing from .env");
  }

  const articles = [];

  for (let page = 1; page <= maxPages; page++) {
    const params = {
      api_token: apiKey,
      language: "en",
      limit: 3,
      page,
      group_similar: true
    };

    if (company.symbol) {
      params.symbols = company.symbol;
      params.filter_entities = true;
    } else {
      params.search = company.search;
    }

    const response = await axios.get(BASE_URL, {
      params
    });

    const pageArticles = response.data.data || [];

    if (pageArticles.length === 0) {
      break;
    }

    for (const article of pageArticles) {
      articles.push({
        ...article,

        targetCompany: {
          key: company.key,
          name: company.name,
          symbol: company.symbol
        }
      });
    }

    if (pageArticles.length < 3) {
      break;
    }
  }

  return articles;
}

async function fetchFinancialNews() {
  try {
    const allArticles = [];

    for (const company of COMPANIES) {
      console.log(`Fetching news for ${company.name}...`);

      const articles = await fetchCompanyNews(
        company,
        5
      );

      console.log(
        `${company.name}: ${articles.length} article(s)`
      );

      allArticles.push(...articles);
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

    return uniqueArticles;

  } catch (error) {
    console.error(
      "MarketAux error:",
      error.response?.data || error.message
    );

    throw error;
  }
}

module.exports = {
  fetchFinancialNews,
  fetchCompanyNews,
  COMPANIES
};