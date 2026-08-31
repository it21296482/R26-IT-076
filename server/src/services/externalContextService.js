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
  { key: "gold", label: "Gold", symbol: "GC=F", unit: "USD per troy ounce" },
  { key: "oil", label: "Crude oil", symbol: "CL=F", unit: "USD per barrel" },
  { key: "vix", label: "VIX Index", symbol: "^VIX", unit: "index points" },
  { key: "usd_lkr", label: "USD/LKR", symbol: "USDLKR=X", unit: "LKR per USD" },
];
const STOCK_FACTOR_EXPOSURES = {
  "JKH.N0000": {
    oil: {
      channel: "Oil can raise fuel, electricity, distribution, hotel, and travel costs. JKH also has bunkering exposure, so the effect can be mixed rather than purely negative.",
      rise: "A sustained oil rise can squeeze transport, retail, leisure, and food margins unless pricing or bunkering income offsets it.",
      fall: "Lower oil can reduce operating and travel costs, although it may also reduce some bunkering-related revenue opportunities.",
    },
    usd_lkr: {
      channel: "A weaker rupee can help foreign-currency tourism and port revenue, but it increases the rupee value of foreign-currency debt and imported costs.",
      rise: "A higher USD/LKR rate is a mixed signal: export-like earnings may improve, while exchange losses and imported costs can rise.",
      fall: "A stronger rupee can reduce exchange-loss and import-cost pressure, but lowers the rupee value of foreign-currency revenue.",
    },
    gold: {
      channel: "Gold has no strong direct operating link to JKH. It mainly reflects global risk appetite, inflation concern, and demand for defensive assets.",
      rise: "Rising gold can indicate risk aversion, which may weigh on travel, investment confidence, and market valuations.",
      fall: "Falling gold can accompany improving risk appetite, but it is not a direct earnings driver for JKH.",
    },
    vix: {
      channel: "The VIX is an indicator of expected volatility in major global equities. Its link to JKH is mainly through tourism demand, foreign investor confidence, and broader risk appetite rather than direct operating revenue.",
      rise: "A sustained VIX rise can signal global risk aversion and weaker confidence around travel, investment, and emerging-market assets.",
      fall: "A lower VIX can accompany calmer global conditions and stronger risk appetite, but it does not guarantee a higher JKH price.",
    },
  },
  "BIL.N0000": {
    oil: {
      channel: "Oil can affect BIL through hotel, plantation, manufacturing, construction, transport, and electricity costs.",
      rise: "A sustained oil rise can increase operating and logistics costs across several businesses and pressure already-thin cash generation.",
      fall: "Lower oil can ease operating and transport costs across the diversified portfolio.",
    },
    usd_lkr: {
      channel: "BIL has overseas and tourism-linked activities, so rupee depreciation can create translation gains, but foreign funding and imported inputs can become more expensive.",
      rise: "A higher USD/LKR rate can improve translated foreign earnings while increasing debt, finance, and import-cost pressure.",
      fall: "A stronger rupee can reduce imported-cost and foreign-liability pressure but may reduce translation gains.",
    },
    gold: {
      channel: "Gold is mainly an indirect signal of inflation and global risk appetite for BIL, not a confirmed direct revenue driver.",
      rise: "Rising gold can signal defensive investor behaviour and broader uncertainty around diversified-market valuations.",
      fall: "Falling gold can accompany stronger risk appetite, but the direct effect on BIL operations is limited.",
    },
    vix: {
      channel: "The VIX is a global risk-appetite indicator. Its link to BIL is indirect through tourism, funding conditions, foreign sentiment, and diversified asset valuations.",
      rise: "A sustained VIX rise can increase global risk aversion and make funding, tourism, or diversified holdings harder to value.",
      fall: "A lower VIX can support calmer investment conditions, but it does not directly determine BIL's operating performance or share price.",
    },
  },
};

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

const fetchCseAspiSnapshot = async (timeoutMs = 12000) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch("https://www.cse.lk/api/aspiData", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "CSE-Insight-Research/1.0",
      },
      body: "",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`CSE ASPI source returned HTTP ${response.status}.`);
    const payload = await response.json();
    const value = Number(payload.value);
    const change = Number(payload.change);
    const changePct = Number(payload.percentage);
    if (![value, change, changePct].every(Number.isFinite)) {
      throw new Error("CSE ASPI source returned an incomplete snapshot.");
    }
    return {
      label: "All Share Price Index (ASPI)",
      source: "Colombo Stock Exchange",
      value: Number(value.toFixed(4)),
      change: Number(change.toFixed(4)),
      changePct: Number(changePct.toFixed(4)),
      date: Number.isFinite(Number(payload.timestamp))
        ? new Date(Number(payload.timestamp)).toISOString().slice(0, 10)
        : null,
    };
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

const regressionSensitivity = (pairs) => {
  if (pairs.length < 2) return { beta: null, rSquared: null };
  const meanStock = pairs.reduce((sum, pair) => sum + pair[0], 0) / pairs.length;
  const meanFactor = pairs.reduce((sum, pair) => sum + pair[1], 0) / pairs.length;
  let covariance = 0;
  let factorVariance = 0;
  for (const [stockReturn, factorReturn] of pairs) {
    covariance += (factorReturn - meanFactor) * (stockReturn - meanStock);
    factorVariance += (factorReturn - meanFactor) ** 2;
  }
  const correlation = pearsonCorrelation(pairs);
  return {
    beta: factorVariance ? covariance / factorVariance : null,
    rSquared: correlation === null ? null : correlation ** 2,
  };
};

const describeAssociation = (correlation) => {
  if (correlation === null) return "There is not enough overlapping data to estimate an association.";
  const magnitude = Math.abs(correlation);
  const strength = magnitude < 0.2 ? "very weak" : magnitude < 0.4 ? "weak" : magnitude < 0.6 ? "moderate" : "strong";
  const direction = correlation >= 0 ? "same-direction" : "opposite-direction";
  return `The observed daily relationship was ${strength} and ${direction}. This is correlation, not proof of cause.`;
};

const classifyMarketComparison = ({ stockChangePct, aspiChangePct }) => {
  if (![stockChangePct, aspiChangePct].every(Number.isFinite)) {
    return {
      classification: "unavailable",
      interpretation: "There was not enough same-session evidence to compare this stock with the wider market.",
    };
  }
  if (stockChangePct < 0 && aspiChangePct < 0) {
    return {
      classification: "broader_market_weakness",
      interpretation: "The stock and the ASPI both declined, so the weakness was shared with the broader market rather than isolated to this company. This does not mean every listed stock declined.",
    };
  }
  if (stockChangePct < 0 && aspiChangePct >= 0) {
    return {
      classification: "stock_specific_weakness",
      interpretation: "The stock declined while the ASPI was flat or higher, so the latest weakness was specific to this stock relative to the broader market.",
    };
  }
  if (stockChangePct >= 0 && aspiChangePct < 0) {
    return {
      classification: "resilient_in_weak_market",
      interpretation: "The stock held up or rose while the ASPI declined, so it showed relative strength against a weaker broader market.",
    };
  }
  return {
    classification: "broader_market_strength",
    interpretation: "The stock and the ASPI were both flat or higher, so the stock participated in broader market strength during the latest session.",
  };
};

const buildMarketComparison = async (symbol, aspiSnapshot) => {
  const rows = await Stock.find({ symbol: String(symbol).toUpperCase() })
    .sort({ tradeDate: -1 })
    .limit(2)
    .select("tradeDate close -_id")
    .lean();
  if (rows.length < 2 || !Number.isFinite(Number(rows[0].close)) || !Number.isFinite(Number(rows[1].close))) {
    return classifyMarketComparison({ stockChangePct: null, aspiChangePct: aspiSnapshot.changePct });
  }
  const stockChangePct = ((Number(rows[0].close) / Number(rows[1].close)) - 1) * 100;
  const stockDate = new Date(rows[0].tradeDate).toISOString().slice(0, 10);
  if (aspiSnapshot.date && stockDate !== aspiSnapshot.date) {
    return {
      stockDate,
      stockChangePct: Number(stockChangePct.toFixed(4)),
      aspiDate: aspiSnapshot.date,
      aspiValue: aspiSnapshot.value,
      aspiChangePct: aspiSnapshot.changePct,
      relativeToAspiPct: null,
      classification: "unavailable",
      interpretation: "The latest stock and ASPI observations were from different dates, so no same-session market comparison was made.",
    };
  }
  return {
    stockDate,
    stockChangePct: Number(stockChangePct.toFixed(4)),
    aspiDate: aspiSnapshot.date,
    aspiValue: aspiSnapshot.value,
    aspiChangePct: aspiSnapshot.changePct,
    relativeToAspiPct: Number((stockChangePct - aspiSnapshot.changePct).toFixed(4)),
    ...classifyMarketComparison({ stockChangePct, aspiChangePct: aspiSnapshot.changePct }),
  };
};


const buildFactorMeaning = ({ symbol, factor, correlation, beta, change30dPct }) => {
  const exposure = STOCK_FACTOR_EXPOSURES[String(symbol).toUpperCase()]?.[factor.key];
  const association = describeAssociation(correlation);
  const estimatedAssociation = Number.isFinite(beta) && Number.isFinite(change30dPct)
    ? beta * change30dPct
    : null;
  const magnitude = Math.abs(correlation || 0);
  const contribution = magnitude < 0.2
    ? "The measured relationship is too weak to treat this factor as a major statistical contributor by itself."
    : `Based on the one-year sensitivity, the factor's 30-day move corresponds to an estimated ${estimatedAssociation >= 0 ? "+" : ""}${estimatedAssociation.toFixed(1)}% stock-return association. This is not a causal attribution.`;
  return {
    businessChannel: exposure?.channel || "This factor can influence costs, demand, currency conditions, or investor confidence.",
    ifFactorRises: exposure?.rise || "A sustained rise may change costs, demand, or market confidence.",
    ifFactorFalls: exposure?.fall || "A sustained fall may change costs, demand, or market confidence.",
    statisticalReading: association,
    contributionEstimate: contribution,
    estimatedAssociated30dStockMovePct: estimatedAssociation === null ? null : Number(estimatedAssociation.toFixed(4)),
  };
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
    const sensitivity = pairs.length >= 20 ? regressionSensitivity(pairs) : { beta: null, rSquared: null };
    const change30dPct = percentChange(result.value.observations, 21);
    const change90dPct = percentChange(result.value.observations, 63);
    factors.push({
      key: factor.key,
      label: factor.label,
      source: "Yahoo Finance chart data",
      sourceSymbol: factor.symbol,
      unit: factor.unit,
      latestDate: result.value.observations.at(-1).date,
      latestValue: Number(result.value.observations.at(-1).close.toFixed(4)),
      change30dPct: Number(change30dPct?.toFixed(4)),
      change90dPct: Number(change90dPct?.toFixed(4)),
      overlappingReturnDays: pairs.length,
      dailyReturnCorrelation: correlation === null ? null : Number(correlation.toFixed(4)),
      sensitivityBeta: sensitivity.beta === null ? null : Number(sensitivity.beta.toFixed(4)),
      explanatorySharePct: sensitivity.rSquared === null ? null : Number((sensitivity.rSquared * 100).toFixed(2)),
      meaning: buildFactorMeaning({ symbol, factor, correlation, beta: sensitivity.beta, change30dPct }),
      interpretation: describeAssociation(correlation),
    });
  });

  if (stockObservations.length < 20) {
    warnings.push("The database does not contain enough selected-stock history for factor association estimates.");
  }
  return { factors, warnings, method: "One-year overlapping daily returns using Pearson correlation and single-factor return sensitivity. Results describe association, not cause." };
};

const collectExternalContext = async ({ symbol, companyName }) => {
  const shortSymbol = String(symbol).split(".")[0];
  const queries = [
    { scope: "company", query: `\"${companyName}\" OR \"${shortSymbol}\" Sri Lanka stock when:90d` },
    { scope: "market", query: `(\"Colombo Stock Exchange\" OR \"Sri Lanka economy\") (inflation OR interest OR rupee OR IMF OR oil OR gold OR war) when:45d` },
    { scope: "global", query: `(Iran OR \"Middle East\" OR geopolitical OR war) (oil OR markets OR \"Sri Lanka\") when:45d` },
  ];
  const [companyNews, marketNews, globalNews, factorResult, aspiResult] = await Promise.allSettled([
    fetchNewsFeed({ ...queries[0], companyName }),
    fetchNewsFeed({ ...queries[1], companyName }),
    fetchNewsFeed({ ...queries[2], companyName }),
    analyzeExternalFactors(symbol),
    fetchCseAspiSnapshot(),
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
  let marketComparison = null;
  let aspiSnapshot = null;
  if (aspiResult.status === "fulfilled") {
    aspiSnapshot = aspiResult.value;
    try {
      marketComparison = await buildMarketComparison(symbol, aspiSnapshot);
    } catch (error) {
      warnings.push(`The selected stock could not be compared with the ASPI: ${error.message}`);
    }
  } else {
    warnings.push(`ASPI data was unavailable: ${aspiResult.reason.message}`);
  }

  return {
    collectedAt: new Date().toISOString(),
    articleCount: uniqueArticles.length,
    sentimentCounts,
    articles: uniqueArticles,
    externalFactors: {
      factors: externalFactors.factors,
      aspiSnapshot,
      marketComparison,
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
  regressionSensitivity,
  buildFactorMeaning,
  classifyMarketComparison,
};
