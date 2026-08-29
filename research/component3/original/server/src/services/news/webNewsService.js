const axios = require("axios");
const cheerio = require("cheerio");

const COMPANIES = require("../../config/companies");

// Web news sources
const WEB_SOURCES = [
  {
    id: "economynext-business",
    name: "EconomyNext",
    type: "economynext",
    url: "https://economynext.com/business/"
  },
  {
    id: "economynext-stocks",
    name: "EconomyNext",
    type: "economynext",
    url: "https://economynext.com/markets/stocks-companies/"
  },
  {
    id: "newsfirst-business",
    name: "NewsFirst",
    type: "newsfirst",
    url: "https://www.newsfirst.lk/business"
  }
];

// Market and macroeconomic keywords
const MARKET_KEYWORDS = [
  "colombo stock exchange",
  "stock market",
  "share market",
  "stocks",
  "cse",
  "aspi",
  "central bank",
  "interest rate",
  "interest rates",
  "monetary policy",
  "inflation",
  "consumer prices",
  "exchange rate",
  "rupee",
  "forex",
  "currency",
  "bond",
  "bonds",
  "treasury",
  "treasury bills",
  "imf",
  "gdp",
  "economic growth",
  "economy",
  "tourism",
  "tourist arrivals",
  "tourism revenue",
  "exports",
  "imports",
  "trade",
  "investment",
  "foreign investment",
  "fdi",
  "oil",
  "oil price",
  "fuel",
  "fuel price",
  "energy",
  "tax",
  "taxation",
  "tariff",
  "banking",
  "banking sector",
  "war",
  "geopolitical",
  "sanctions",
  "global markets"
];

// Clearly irrelevant categories
const EXCLUDE_KEYWORDS = [
  "football",
  "cricket",
  "rugby",
  "saff",
  "fifa",
  "tournament",
  "sports"
];

// Normalize text for matching
function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/<[^>]*>/g, " ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Clean extracted text
function cleanText(text) {
  return String(text || "")
    .replace(/\s+/g, " ")
    .trim();
}

// Clean NewsFirst boilerplate
function cleanDescription(text) {
  return cleanText(text)
    .replace(/&nbsp;/gi, " ")
    .replace(/Get the latest breaking news[\s\S]*$/i, "")
    .replace(/Read more[\s\S]*$/i, "")
    .trim();
}

// Delay helper
function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

// Fetch page with retry support
async function getPage(url, retries = 2) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await axios.get(url, {
        timeout: 15000,
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
          Accept:
            "text/html,application/xhtml+xml"
        }
      });
    } catch (error) {
      if (attempt === retries) {
        throw error;
      }

      await sleep(1000);
    }
  }
}

// Clean URL for deduplication
function cleanUrl(url) {
  if (!url) {
    return "";
  }

  try {
    const parsed = new URL(url);

    parsed.hash = "";

    return parsed.toString();
  } catch {
    return url;
  }
}

// Parse normal and EconomyNext date formats
function parsePublishedDate(value) {
  if (!value) {
    return null;
  }

  const normalDate = new Date(value);

  if (!Number.isNaN(normalDate.getTime())) {
    return normalDate;
  }

  const economyNextMatch = String(value).match(
    /(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})/i
  );

  if (!economyNextMatch) {
    return null;
  }

  const [, month, day, year] =
    economyNextMatch;

  const parsed =
    new Date(`${month} ${day}, ${year}`);

  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed;
}

// Find configured companies mentioned in article
function findMatchingCompanies(article) {
  const text = normalize(
    `${article.title || ""} ${article.description || ""}`
  );

  return COMPANIES.filter((company) => {
    return company.searchTerms.some((term) => {
      const normalizedTerm =
        normalize(term);

      if (normalizedTerm.length <= 3) {
        return text
          .split(" ")
          .includes(normalizedTerm);
      }

      return text.includes(
        normalizedTerm
      );
    });
  });
}

// Detect market-wide or macroeconomic news
function isMarketImpactNews(article) {
  const text = normalize(
    `${article.title || ""} ${article.description || ""}`
  );

  return MARKET_KEYWORDS.some((keyword) => {
    return text.includes(
      normalize(keyword)
    );
  });
}

// Remove obvious sports stories
function isExcludedNews(article) {
  const title =
    normalize(article.title || "");

  const words =
    title.split(" ");

  return EXCLUDE_KEYWORDS.some((keyword) => {
    return words.includes(
      normalize(keyword)
    );
  });
}

// Check article freshness
function isRecentArticle(
  publishedAt,
  days = 180
) {
  if (!publishedAt) {
    return true;
  }

  const articleDate =
    parsePublishedDate(publishedAt);

  if (!articleDate) {
    return true;
  }

  const cutoff = new Date();

  cutoff.setDate(
    cutoff.getDate() - days
  );

  return articleDate >= cutoff;
}

// Require at least usable headline data
function hasUsableContent(article) {
  return Boolean(
    article.title &&
    article.title.trim().length >= 15
  );
}

// Extract date-like text from a listing container
function findListingDate(container) {
  const timeElement =
    container.find("time").first();

  const datetime =
    timeElement.attr("datetime");

  if (datetime) {
    return cleanText(datetime);
  }

  const timeText =
    cleanText(timeElement.text());

  if (timeText) {
    return timeText;
  }

  const containerText =
    cleanText(container.text());

  const economyNextDate =
    containerText.match(
      /\d{1,2}:\d{2}\s*(?:am|pm),?\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}/i
    );

  if (economyNextDate) {
    return economyNextDate[0];
  }

  return null;
}

// Read EconomyNext listing pages
async function fetchEconomyNext(source) {
  const response =
    await getPage(source.url);

  const $ =
    cheerio.load(response.data);

  const articles = [];

  $("a").each((_, element) => {
    const anchor =
      $(element);

    const title =
      cleanText(anchor.text());

    let url =
      anchor.attr("href");

    if (
      !title ||
      title.length < 15 ||
      !url
    ) {
      return;
    }

    if (url.startsWith("/")) {
      url =
        `https://economynext.com${url}`;
    }

    if (
      !url.startsWith(
        "https://economynext.com/"
      )
    ) {
      return;
    }

    const lowerTitle =
      title.toLowerCase();

    if (
      url === source.url ||
      url.includes("/category/") ||
      url.includes("/author/") ||
      url.includes("/tag/") ||
      lowerTitle === "business" ||
      lowerTitle === "economy" ||
      lowerTitle === "general economy" ||
      lowerTitle === "stocks & companies" ||
      lowerTitle === "stocks and companies"
    ) {
      return;
    }

    // Find closest listing-card container
    const container =
      anchor.closest(
        "article, .post, .news-item, .item, .card, li, div"
      );

    // Try to get summary directly from listing
    const description =
      cleanText(
        container
          .find("p")
          .first()
          .text()
      );

    // Try to get date directly from listing
    const publishedAt =
      findListingDate(container);

    articles.push({
      title,
      description,
      url: cleanUrl(url),
      source: source.name,
      sourceType: source.type,
      newsProvider: "web",
      published_at: publishedAt
    });
  });

  return articles;
}

// Read NewsFirst business listing
async function fetchNewsFirst(source) {
  const response =
    await getPage(source.url);

  const $ =
    cheerio.load(response.data);

  const articles = [];

  $("a").each((_, element) => {
    const anchor =
      $(element);

    const rawText =
      cleanText(anchor.text());

    let url =
      anchor.attr("href");

    if (
      !rawText ||
      rawText.length < 15 ||
      !url
    ) {
      return;
    }

    if (url.startsWith("/")) {
      url =
        `https://www.newsfirst.lk${url}`;
    }

    if (
      !url.startsWith(
        "https://www.newsfirst.lk/"
      )
    ) {
      return;
    }

    if (
      url === source.url ||
      url.endsWith("/business") ||
      url.endsWith("/business/") ||
      url.includes("/tag/") ||
      url.includes("/category/")
    ) {
      return;
    }

    const container =
      anchor.closest(
        "article, .post, .news-item, .item, .card, li, div"
      );

    const description =
      cleanDescription(
        container
          .find("p")
          .first()
          .text()
      );

    // NewsFirst URLs usually contain the publication date
    let publishedAt = null;

    const dateMatch =
      url.match(
        /\/(20\d{2})\/(\d{2})\/(\d{2})\//
      );

    if (dateMatch) {
      const [, year, month, day] =
        dateMatch;

      publishedAt =
        `${year}-${month}-${day}T00:00:00`;
    }

    articles.push({
      title: rawText,
      description,
      url: cleanUrl(url),
      source: source.name,
      sourceType: source.type,
      newsProvider: "web",
      published_at: publishedAt
    });
  });

  return articles;
}

// Extract full EconomyNext article as fallback
async function extractEconomyNextArticle(
  article
) {
  try {
    const response =
      await getPage(
        article.url,
        1
      );

    const $ =
      cheerio.load(response.data);

    let title =
      cleanText(
        $('meta[property="og:title"]')
          .attr("content") ||
        $("h1").first().text() ||
        article.title
      );

    title = title.replace(
      /\s*\|\s*EconomyNext\s*$/i,
      ""
    );

    const metaDescription =
      cleanText(
        $('meta[property="og:description"]')
          .attr("content") ||
        $('meta[name="description"]')
          .attr("content") ||
        ""
      );

    const paragraphs = [];

    $(
      "article p, .entry-content p, .post-content p, .article-content p"
    ).each((_, element) => {
      const text =
        cleanText(
          $(element).text()
        );

      if (text.length >= 30) {
        paragraphs.push(text);
      }
    });

    const articleText =
      paragraphs
        .slice(0, 8)
        .join(" ");

    let publishedAt =
      $('meta[property="article:published_time"]')
        .attr("content") ||
      $("time")
        .first()
        .attr("datetime") ||
      article.published_at ||
      null;

    if (!publishedAt) {
      const bodyText =
        cleanText(
          $("body").text()
        );

      const dateMatch =
        bodyText.match(
          /\d{1,2}:\d{2}\s*(?:am|pm),\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}/i
        );

      if (dateMatch) {
        publishedAt =
          dateMatch[0];
      }
    }

    return {
      ...article,
      title,
      description:
        articleText ||
        metaDescription ||
        article.description ||
        "",
      published_at:
        publishedAt,
      extractionFailed: false
    };
  } catch (error) {
    console.warn(
      `EconomyNext extraction failed: ${article.url}`
    );

    return {
      ...article,
      extractionFailed: true
    };
  }
}

// Extract full NewsFirst article as fallback
async function extractNewsFirstArticle(
  article
) {
  try {
    const response =
      await getPage(
        article.url,
        1
      );

    const $ =
      cheerio.load(response.data);

    const title =
      cleanText(
        $('meta[property="og:title"]')
          .attr("content") ||
        $("h1").first().text() ||
        article.title
      );

    const metaDescription =
      cleanDescription(
        $('meta[property="og:description"]')
          .attr("content") ||
        $('meta[name="description"]')
          .attr("content") ||
        ""
      );

    const paragraphs = [];

    $(
      "article p, .article-content p, .news-content p, .content p, main p"
    ).each((_, element) => {
      const text =
        cleanDescription(
          $(element).text()
        );

      if (text.length >= 30) {
        paragraphs.push(text);
      }
    });

    const articleText =
      cleanDescription(
        paragraphs
          .slice(0, 8)
          .join(" ")
      );

    let publishedAt =
      $('meta[property="article:published_time"]')
        .attr("content") ||
      $("time")
        .first()
        .attr("datetime") ||
      article.published_at ||
      null;

    if (!publishedAt) {
      const dateMatch =
        article.url.match(
          /\/(20\d{2})\/(\d{2})\/(\d{2})\//
        );

      if (dateMatch) {
        const [, year, month, day] =
          dateMatch;

        publishedAt =
          `${year}-${month}-${day}T00:00:00`;
      }
    }

    return {
      ...article,
      title,
      description:
        articleText ||
        metaDescription ||
        article.description ||
        "",
      published_at:
        publishedAt,
      extractionFailed: false
    };
  } catch (error) {
    console.warn(
      `NewsFirst extraction failed: ${article.url}`
    );

    return {
      ...article,
      extractionFailed: true
    };
  }
}

// Route article to correct extractor
async function extractFullArticle(
  article
) {
  if (
    article.sourceType ===
    "economynext"
  ) {
    return extractEconomyNextArticle(
      article
    );
  }

  if (
    article.sourceType ===
    "newsfirst"
  ) {
    return extractNewsFirstArticle(
      article
    );
  }

  return article;
}

// Route source to correct listing parser
async function fetchSourceArticles(
  source
) {
  if (
    source.type ===
    "economynext"
  ) {
    return fetchEconomyNext(
      source
    );
  }

  if (
    source.type ===
    "newsfirst"
  ) {
    return fetchNewsFirst(
      source
    );
  }

  return [];
}

// Fetch all relevant web news
async function fetchWebNews() {
  const allCandidates = [];

  // Fetch listing pages first
  for (const source of WEB_SOURCES) {
    console.log(
      `Checking ${source.name}: ${source.id}...`
    );

    try {
      const candidates =
        await fetchSourceArticles(
          source
        );

      console.log(
        `${source.name} (${source.id}): ${candidates.length} candidate article(s)`
      );

      allCandidates.push(
        ...candidates
      );
    } catch (error) {
      console.error(
        `${source.name} (${source.id}) listing failed:`,
        error.response?.status ||
          error.message
      );
    }
  }

  // Deduplicate before opening any article pages
  const uniqueCandidates =
    Array.from(
      new Map(
        allCandidates.map(
          (article) => [
            article.url,
            article
          ]
        )
      ).values()
    );

  const collected = [];

  for (
    const candidate of
      uniqueCandidates
  ) {
    // Remove obvious sports stories first
    if (
      isExcludedNews(
        candidate
      )
    ) {
      continue;
    }

    // Cheap headline and listing-summary relevance check
    const headlineCompanies =
      findMatchingCompanies(
        candidate
      );

    const headlineMarketImpact =
      isMarketImpactNews(
        candidate
      );

    if (
      headlineCompanies.length === 0 &&
      !headlineMarketImpact
    ) {
      continue;
    }

    // Start with listing-page information
    let article = {
      ...candidate
    };

    // Only open article page if important information is missing
    const needsExtraction =
      !candidate.description ||
      candidate.description.trim().length < 30 ||
      !candidate.published_at;

    if (needsExtraction) {
      const extracted =
        await extractFullArticle(
          candidate
        );

      article = {
        ...candidate,

        title:
          extracted.title ||
          candidate.title,

        description:
          extracted.description ||
          candidate.description ||
          "",

        published_at:
          extracted.published_at ||
          candidate.published_at ||
          null,

        extractionFailed:
          Boolean(
            extracted.extractionFailed
          )
      };

      // Reduce pressure on source websites
      await sleep(600);
    }

    // Clean NewsFirst description
    if (
      article.sourceType ===
      "newsfirst"
    ) {
      article.description =
        cleanDescription(
          article.description
        );
    }

    // Remove excluded articles again after full extraction
    if (
      isExcludedNews(
        article
      )
    ) {
      console.log(
        `Skipping excluded article: ${article.title}`
      );

      continue;
    }

    // Require a usable headline
    if (
      !hasUsableContent(
        article
      )
    ) {
      continue;
    }

    // Apply freshness check only when a date is available
    if (
      article.published_at &&
      !isRecentArticle(
        article.published_at,
        180
      )
    ) {
      continue;
    }

    // Recalculate relevance using final text
    const matchingCompanies =
      findMatchingCompanies(
        article
      );

    const marketImpact =
      isMarketImpactNews(
        article
      );

    if (
      matchingCompanies.length === 0 &&
      !marketImpact
    ) {
      continue;
    }

    collected.push({
  ...article,

  newsType:
    matchingCompanies.length > 0
      ? "company"
      : "market",

  targetCompanies:
    matchingCompanies.map(
      (company) => ({
        key: company.key,
        name: company.name,
        symbol: company.symbol
      })
    ),

  marketImpact,

  // Mark whether publication date is usable
  hasValidDate: Boolean(
    parsePublishedDate(
      article.published_at
    )
  )
});
  }

  // Remove duplicate URLs
  const uniqueByUrl =
    Array.from(
      new Map(
        collected.map(
          (article) => [
            article.url,
            article
          ]
        )
      ).values()
    );

  // Remove duplicate titles
  const seenTitles =
    new Set();

  const uniqueArticles =
    uniqueByUrl.filter(
      (article) => {
        const titleKey =
          normalize(
            article.title
          );

        if (
          !titleKey ||
          seenTitles.has(
            titleKey
          )
        ) {
          return false;
        }

        seenTitles.add(
          titleKey
        );

        return true;
      }
    );

  // Sort newest articles first
  uniqueArticles.sort(
    (a, b) => {
      const dateA =
        parsePublishedDate(
          a.published_at
        );

      const dateB =
        parsePublishedDate(
          b.published_at
        );

      return (
        (dateB?.getTime() || 0) -
        (dateA?.getTime() || 0)
      );
    }
  );

  console.log(
    `Total relevant web articles: ${uniqueArticles.length}`
  );

  return uniqueArticles;
}

// Export service functions
module.exports = {
  fetchWebNews,
  fetchEconomyNext,
  fetchNewsFirst,
  extractEconomyNextArticle,
  extractNewsFirstArticle,
  extractFullArticle,
  findMatchingCompanies,
  isMarketImpactNews,
  isExcludedNews,
  isRecentArticle,
  hasUsableContent,
  parsePublishedDate,
  WEB_SOURCES
};