const Parser = require("rss-parser");
const Stock = require("../models/Stock");

const parser = new Parser();
const POSITIVE_TERMS = [
  "growth", "profit", "profits", "gain", "gains", "higher", "recovery", "strong",
  "improved", "increase", "investment", "upgrade", "surge", "record profit",
];
const NEGATIVE_TERMS = [
  "loss", "losses", "decline", "lower", "drop", "weak", "debt", "inflation",
  "crisis", "risk", "war", "sanctions", "volatile", "downgrade", "profit falls",
];
const EVENT_GROUPS = {
  company_performance: ["earnings", "revenue", "profit", "loss", "dividend", "results"],
  interest_rates: ["interest rate", "policy rate", "central bank"],
  currency: ["exchange rate", "rupee", "currency", "usd/lkr"],
  inflation: ["inflation", "cost of living"],
  commodities: ["oil", "fuel", "gold", "commodity"],
  policy_and_trade: ["imf", "budget", "tax", "exports", "imports", "trade"],
  geopolitical: ["war", "sanctions", "geopolitical", "conflict"],
};
const FACTORS = [
  { key: "gold", label: "Gold", symbol: "GC=F" },
  { key: "oil", label: "Crude oil", symbol: "CL=F" },
  { key: "usd_lkr", label: "USD/LKR", symbol: "USDLKR=X" },
];

const normalize = (value) => String(value || "")
  .toLowerCase()
  .replace(/<[^>]*>/g, " ")
  .replace(/[^a-z0-9\s/.-]/g, " ")
  .replace(/\s+/g, " ")
  .trim();

const countTerms = (text, terms) => terms.reduce(
  (count, term) => count + (text.includes(normalize(term)) ? 1 : 0),
  0
);

const analyzeSentiment = (value) => {
  const text = normalize(value);
  const positiveCount = countTerms(text, POSITIVE_TERMS);
  const negativeCount = countTerms(text, NEGATIVE_TERMS);
  const total = positiveCount + negativeCount;
  const score = total ? (positiveCount - negativeCount) / total : 0;
  const label = score >= 0.2 ? "positive" : score <= -0.2 ? "negative" : "neutral";
  return { label, score: Number(score.toFixed(4)), matchedTermCount: total };
};

const eventTags = (value) => {
  const text = normalize(value);
  return Object.entries(EVENT_GROUPS)
    .filter(([, terms]) => terms.some((term) => text.includes(normalize(term))))
    .map(([key]) => key);
};

const fetchText = async (url, timeoutMs = 12000) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      headers: { "User-Agent": "CSE-Insight-Research/1.0" },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Source returned HTTP ${response.status}.`);
    }
    return await response.text();
  } finally {
    clearTimeout(timeout);
  }
};

const buildGoogleNewsUrl = (query) => (
  `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=en-LK&gl=LK&ceid=LK:en`
);

const fetchNewsFeed = async ({ query, scope, companyName }) => {
  const xml = await fetchText(buildGoogleNewsUrl(query));
  const feed = await parser.parseString(xml);
  return (feed.items || []).slice(0, 30).map((item) => {
    const title = String(item.title || "").replace(/\s+-\s+[^-]+$/, "").trim();
    const description = String(item.contentSnippet || item.content || "").trim();
    const analysisText = `${title}. ${description}`;
    const publishedAt = item.isoDate || item.pubDate || null;
    const date = publishedAt ? new Date(publishedAt) : null;
    return {
      title,
      description,
      url: item.link || "",
      source: item.creator || item.source || "Google News",
      publishedAt: date && !Number.isNaN(date.getTime()) ? date.toISOString() : null,
      scope,
      relevance: scope === "company"
        ? `The search result matched the selected company, ${companyName}.`
        : scope === "global"
          ? "The result matched global events that may influence energy prices or investor confidence."
          : "The result matched CSE or macroeconomic context terms.",
      sentiment: analyzeSentiment(analysisText),
      eventTags: eventTags(analysisText),
    };
  }).filter((item) => item.title && item.url && item.publishedAt);
};

const deduplicateNews = (articles) => {
  const unique = new Map();
  for (const article of articles) {
    const key = normalize(article.title);
    if (!key || unique.has(key)) continue;
    unique.set(key, article);
  }
  return [...unique.values()].sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));
};

const fetchYahooSeries = async (factor) => {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(factor.symbol)}?range=1y&interval=1d`;
  const payload = JSON.parse(await fetchText(url));
  const result = payload.chart?.result?.[0];
  const timestamps = result?.timestamp || [];
  const closes = result?.indicators?.quote?.[0]?.close || [];
  const observations = timestamps.map((timestamp, index) => ({
    date: new Date(timestamp * 1000).toISOString().slice(0, 10),
    close: Number(closes[index]),
  })).filter((row) => Number.isFinite(row.close) && row.close > 0);
  if (observations.length < 30) {
    throw new Error(`Not enough ${factor.label} observations were returned.`);
  }
  return { ...factor, observations };
};

const percentChange = (observations, sessions) => {
  const end = observations.at(-1)?.close;
  const start = observations.at(Math.max(0, observations.length - 1 - sessions))?.close;
  if (!Number.isFinite(start) || !Number.isFinite(end) || start === 0) return null;
  return ((end / start) - 1) * 100;
};

const returnMap = (observations) => {
  const values = new Map();
  for (let index = 1; index < observations.length; index += 1) {
    const previous = observations[index - 1].close;
    const current = observations[index].close;
    if (previous > 0 && current > 0) {
      values.set(observations[index].date, (current / previous) - 1);
    }
  }
  return values;
};

const pearsonCorrelation = (pairs) => {
  if (pairs.length < 2) return null;
  const meanX = pairs.reduce((sum, pair) => sum + pair[0], 0) / pairs.length;
  const meanY = pairs.reduce((sum, pair) => sum + pair[1], 0) / pairs.length;
  let numerator = 0;
  let denominatorX = 0;
  let denominatorY = 0;
  for (const [x, y] of pairs) {
    numerator += (x - meanX) * (y - meanY);
    denominatorX += (x - meanX) ** 2;
    denominatorY += (y - meanY) ** 2;
  }
  const denominator = Math.sqrt(denominatorX * denominatorY);
  return denominator ? numerator / denominator : null;
};

const describeAssociation = (correlation) => {
  if (correlation === null) return "There is not enough overlapping data to estimate an association.";
  const magnitude = Math.abs(correlation);
  const strength = magnitude < 0.2 ? "very weak" : magnitude < 0.4 ? "weak" : magnitude < 0.6 ? "moderate" : "strong";
  const direction = correlation >= 0 ? "same-direction" : "opposite-direction";
  return `The observed daily relationship was ${strength} and ${direction}. This is correlation, not proof of cause.`;
};

const analyzeExternalFactors = async (symbol) => {
  const stockRows = await Stock.find({ symbol: String(symbol).toUpperCase() })
    .sort({ tradeDate: 1 })
    .select("tradeDate close -_id")
    .lean();
  const stockObservations = stockRows.map((row) => ({
    date: new Date(row.tradeDate).toISOString().slice(0, 10),
    close: Number(row.close),
  })).filter((row) => Number.isFinite(row.close) && row.close > 0).slice(-370);
  const stockReturns = returnMap(stockObservations);
  const factorResults = await Promise.allSettled(FACTORS.map(fetchYahooSeries));
  const warnings = [];
  const factors = [];

  factorResults.forEach((result, index) => {
    const factor = FACTORS[index];
    if (result.status === "rejected") {
      warnings.push(`${factor.label} data was unavailable: ${result.reason.message}`);
      return;
    }
    const factorReturns = returnMap(result.value.observations);
    const pairs = [];
    for (const [date, stockReturn] of stockReturns) {
      if (factorReturns.has(date)) pairs.push([stockReturn, factorReturns.get(date)]);
    }
    const correlation = pairs.length >= 20 ? pearsonCorrelation(pairs) : null;
    factors.push({
      key: factor.key,
      label: factor.label,
      source: "Yahoo Finance chart data",
      sourceSymbol: factor.symbol,
      latestDate: result.value.observations.at(-1).date,
      change30dPct: Number(percentChange(result.value.observations, 21)?.toFixed(4)),
      change90dPct: Number(percentChange(result.value.observations, 63)?.toFixed(4)),
      overlappingReturnDays: pairs.length,
      dailyReturnCorrelation: correlation === null ? null : Number(correlation.toFixed(4)),
      interpretation: describeAssociation(correlation),
    });
  });

  if (stockObservations.length < 20) {
    warnings.push("The database does not contain enough selected-stock history for factor association estimates.");
  }
  return { factors, warnings, method: "Pearson correlation of overlapping daily returns over the latest available year." };
};

const collectExternalContext = async ({ symbol, companyName }) => {
  const shortSymbol = String(symbol).split(".")[0];
  const queries = [
    { scope: "company", query: `\"${companyName}\" OR \"${shortSymbol}\" Sri Lanka stock when:90d` },
    { scope: "market", query: `(\"Colombo Stock Exchange\" OR \"Sri Lanka economy\") (inflation OR interest OR rupee OR IMF OR oil OR gold OR war) when:45d` },
    { scope: "global", query: `(Iran OR \"Middle East\" OR geopolitical OR war) (oil OR markets OR \"Sri Lanka\") when:45d` },
  ];
  const [companyNews, marketNews, globalNews, factorResult] = await Promise.allSettled([
    fetchNewsFeed({ ...queries[0], companyName }),
    fetchNewsFeed({ ...queries[1], companyName }),
    fetchNewsFeed({ ...queries[2], companyName }),
    analyzeExternalFactors(symbol),
  ]);
  const warnings = [];
  const articles = [];
  for (const result of [companyNews, marketNews, globalNews]) {
    if (result.status === "fulfilled") articles.push(...result.value);
    else warnings.push(`A news source request failed: ${result.reason.message}`);
  }
  const uniqueArticles = deduplicateNews(articles).slice(0, 30);
  const sentimentCounts = { positive: 0, neutral: 0, negative: 0 };
  uniqueArticles.forEach((article) => { sentimentCounts[article.sentiment.label] += 1; });
  const externalFactors = factorResult.status === "fulfilled"
    ? factorResult.value
    : { factors: [], warnings: [`External factor data failed: ${factorResult.reason.message}`], method: "Unavailable" };
  warnings.push(...externalFactors.warnings);

  return {
    collectedAt: new Date().toISOString(),
    articleCount: uniqueArticles.length,
    sentimentCounts,
    articles: uniqueArticles,
    externalFactors: {
      factors: externalFactors.factors,
      method: externalFactors.method,
      causalWarning: "Observed associations do not prove that a global factor caused the stock movement.",
    },
    warnings,
    evaluationStatus: "Research evaluation metrics must be established on a labelled CSE news dataset.",
  };
};

module.exports = {
  analyzeSentiment,
  collectExternalContext,
  deduplicateNews,
  describeAssociation,
  eventTags,
  pearsonCorrelation,
};
