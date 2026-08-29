const {
  fetchFinancialNews
} = require("./marketAuxService");

const {
  fetchWebNews,
  parsePublishedDate
} = require("./webNewsService");

// Normalize text for duplicate checking
function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/<[^>]*>/g, " ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Parse article dates from either service
function getArticleDate(article) {
  if (!article.published_at) {
    return null;
  }

  const parsed =
    parsePublishedDate(
      article.published_at
    );

  if (parsed) {
    return parsed;
  }

  const normalDate =
    new Date(
      article.published_at
    );

  if (
    Number.isNaN(
      normalDate.getTime()
    )
  ) {
    return null;
  }

  return normalDate;
}

// Convert MarketAux article into common format
function normalizeMarketAuxArticle(article) {
  const targetCompanies =
    article.targetCompany
      ? [article.targetCompany]
      : [];

  const normalized = {
    title: article.title || "",

    description:
      article.description ||
      article.snippet ||
      "",

    url:
      article.url || "",

    source:
      article.source ||
      article.source_domain ||
      "MarketAux",

    newsProvider:
      "marketaux",

    published_at:
      article.published_at ||
      null,

    newsType:
      targetCompanies.length > 0
        ? "company"
        : "market",

    targetCompanies,

    marketImpact: false
  };

  return {
    ...normalized,

    // Mark whether MarketAux date is usable
    hasValidDate:
      Boolean(
        getArticleDate(
          normalized
        )
      )
  };
}

// Convert web article into common format
function normalizeWebArticle(article) {
  return {
    title:
      article.title || "",

    description:
      article.description || "",

    url:
      article.url || "",

    source:
      article.source || "Web",

    newsProvider:
      article.newsProvider ||
      "web",

    published_at:
      article.published_at ||
      null,

    newsType:
      article.newsType ||
      "market",

    targetCompanies:
      article.targetCompanies ||
      [],

    marketImpact:
      Boolean(
        article.marketImpact
      ),

    // Preserve value from webNewsService
    hasValidDate:
      Boolean(
        article.hasValidDate
      ),

    extractionFailed:
      Boolean(
        article.extractionFailed
      )
  };
}

// Build text passed into sentiment/NLP
function buildAnalysisText(article) {
  const title =
    String(
      article.title || ""
    ).trim();

  const description =
    String(
      article.description || ""
    ).trim();

  if (description) {
    return `${title}. ${description}`;
  }

  return title;
}

// Prefer the best copy of duplicate articles
function deduplicateArticles(articles) {
  const articleMap =
    new Map();

  for (const article of articles) {
    const titleKey =
      normalize(
        article.title
      );

    if (!titleKey) {
      continue;
    }

    const existing =
      articleMap.get(
        titleKey
      );

    if (!existing) {
      articleMap.set(
        titleKey,
        article
      );

      continue;
    }

    // Prefer copy with a valid publication date
    if (
      !existing.hasValidDate &&
      article.hasValidDate
    ) {
      articleMap.set(
        titleKey,
        article
      );

      continue;
    }

    // If date quality is equal, prefer richer content
    const existingLength =
      String(
        existing.description ||
        ""
      ).length;

    const newLength =
      String(
        article.description ||
        ""
      ).length;

    if (
      article.hasValidDate ===
        existing.hasValidDate &&
      newLength >
        existingLength
    ) {
      articleMap.set(
        titleKey,
        article
      );
    }
  }

  return Array.from(
    articleMap.values()
  );
}

// Collect all available news sources
async function collectNews() {
  console.log(
    "Collecting unified financial news..."
  );

  const allArticles = [];

  // Fetch MarketAux safely
  try {
    const marketAuxArticles =
      await fetchFinancialNews();

    console.log(
      `MarketAux collected: ${marketAuxArticles.length}`
    );

    for (
      const article of
        marketAuxArticles
    ) {
      allArticles.push(
        normalizeMarketAuxArticle(
          article
        )
      );
    }
  } catch (error) {
    console.error(
      "MarketAux collection failed:",
      error.response?.data ||
        error.message
    );
  }

  // Fetch EconomyNext and NewsFirst
  try {
    const webArticles =
      await fetchWebNews();

    console.log(
      `Web news collected: ${webArticles.length}`
    );

    for (
      const article of
        webArticles
    ) {
      allArticles.push(
        normalizeWebArticle(
          article
        )
      );
    }
  } catch (error) {
    console.error(
      "Web news collection failed:",
      error.response?.data ||
        error.message
    );
  }

  // Remove duplicate stories and keep best copy
  const uniqueArticles =
    deduplicateArticles(
      allArticles
    );

  // Add NLP-ready text and verify dates
  const preparedArticles =
    uniqueArticles.map(
      (article) => ({
        ...article,

        analysisText:
          buildAnalysisText(
            article
          ),

        hasValidDate:
          Boolean(
            getArticleDate(
              article
            )
          )
      })
    );

  // Keep only dated articles for production analysis
  const validArticles =
    preparedArticles.filter(
      (article) =>
        article.hasValidDate
    );

  // Sort newest first
  validArticles.sort(
    (a, b) => {
      const dateA =
        getArticleDate(a);

      const dateB =
        getArticleDate(b);

      return (
        (dateB?.getTime() || 0) -
        (dateA?.getTime() || 0)
      );
    }
  );

  console.log(
    `Total unified articles: ${validArticles.length}`
  );

  return validArticles;
}

module.exports = {
  collectNews,
  normalizeMarketAuxArticle,
  normalizeWebArticle,
  buildAnalysisText,
  deduplicateArticles,
  getArticleDate
};