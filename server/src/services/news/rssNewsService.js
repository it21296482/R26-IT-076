const Parser = require("rss-parser");
const parser = new Parser();

const COMPANIES = require("../../config/companies");
const NEWS_SOURCES = require("../../config/newsSources");

// -------------------------------------
// Normalize text
// -------------------------------------

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/<[^>]*>/g, " ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// -------------------------------------
// Company matching
// -------------------------------------

function findMatchingCompanies(article) {
  const text = normalize(
    `${article.title || ""} ${article.description || ""}`
  );

  return COMPANIES.filter((company) =>
    company.searchTerms.some((term) => {
      const normalizedTerm = normalize(term);

      if (normalizedTerm.length <= 3) {
        return text.split(" ").includes(normalizedTerm);
      }

      return text.includes(normalizedTerm);
    })
  );
}

// -------------------------------------
// Market-wide news detection
// -------------------------------------

const MARKET_KEYWORDS = [
  "colombo stock exchange",
  "cse",
  "stock market",
  "share market",
  "central bank",
  "interest rate",
  "inflation",
  "exchange rate",
  "rupee",
  "imf",
  "budget",
  "tax",
  "exports",
  "imports",
  "tourism",
  "oil",
  "fuel",
  "banking",
  "economy",
  "gdp",
  "foreign investment",
  "trade",
  "war",
  "geopolitical"
];

function isMarketImpactNews(article) {
  const text = normalize(
    `${article.title || ""} ${article.description || ""}`
  );

  return MARKET_KEYWORDS.some(keyword =>
    text.includes(normalize(keyword))
  );
}

// -------------------------------------
// Fetch all RSS news
// -------------------------------------

async function fetchRSSNews() {
  const articles = [];

  for (const source of NEWS_SOURCES) {
    console.log(`Checking ${source.name}...`);

    for (const feed of source.feeds) {
      try {
        const rss = await parser.parseURL(feed);

        for (const item of rss.items || []) {

          const article = {
            title: item.title || "",
            description:
              item.contentSnippet ||
              item.content ||
              item.summary ||
              "",
            url: item.link,
            source: source.name,
            newsProvider: "rss",
            published_at:
              item.isoDate ||
              item.pubDate ||
              null
          };

          const companies =
            findMatchingCompanies(article);

          const marketImpact =
            isMarketImpactNews(article);

          if (
            companies.length === 0 &&
            !marketImpact
          ) {
            continue;
          }

          articles.push({
            ...article,
            targetCompanies: companies.map(c => ({
              key: c.key,
              name: c.name,
              symbol: c.symbol
            })),
            marketImpact
          });
        }

      } catch (err) {
        console.error(
          `${source.name} RSS failed:`,
          err.message
        );
      }
    }
  }

  // Remove duplicates
  const unique = Array.from(
    new Map(
      articles.map(a => [a.url, a])
    ).values()
  );

  // Sort newest first
  unique.sort(
    (a, b) =>
      new Date(b.published_at) -
      new Date(a.published_at)
  );

  console.log(
    `RSS articles collected: ${unique.length}`
  );

  return unique;
}

module.exports = {
  fetchRSSNews
};