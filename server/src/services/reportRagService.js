const DEFAULT_CHUNK_SIZE = 1800;
const DEFAULT_CHUNK_OVERLAP = 260;
const DEFAULT_TOP_K = 18;

const STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "by",
  "for",
  "from",
  "in",
  "into",
  "is",
  "it",
  "of",
  "on",
  "or",
  "that",
  "the",
  "their",
  "this",
  "to",
  "with",
]);

const INVESTOR_RETRIEVAL_QUERIES = [
  "company name annual report reporting year principal activities business overview",
  "revenue turnover income gross profit operating profit profit after tax net profit earnings per share EPS",
  "total assets total liabilities total equity borrowings debt cash and cash equivalents",
  "cash flow operating activities investing activities financing activities capital expenditure",
  "dividend shareholders stated capital shares market price public holding",
  "risk management liquidity risk credit risk market risk interest rate foreign exchange operational regulatory",
  "independent auditor report audit opinion true and fair view",
  "chairman chief executive officer review future outlook strategy expansion challenges",
  "strategic highlights business highlights performance highlights investor information",
];

// These terms keep the retriever focused on investor-useful annual-report sections.
const IMPORTANT_TERMS = [
  "revenue",
  "turnover",
  "profit",
  "earnings",
  "eps",
  "assets",
  "liabilities",
  "equity",
  "cash",
  "borrowings",
  "debt",
  "dividend",
  "shareholders",
  "risk",
  "audit",
  "auditor",
  "opinion",
  "outlook",
  "strategy",
  "highlights",
];

const normalizeWhitespace = (value) => value.replace(/\s+/g, " ").trim();

const tokenize = (value) =>
  normalizeWhitespace(value)
    .toLowerCase()
    .replace(/[^a-z0-9.%/-]+/g, " ")
    .split(" ")
    .filter((token) => token.length > 2 && !STOP_WORDS.has(token));

const estimatePageNumber = (startIndex, totalLength, estimatedPageCount) => {
  if (!totalLength || !estimatedPageCount) {
    return null;
  }
  return Math.max(1, Math.min(estimatedPageCount, Math.ceil((startIndex / totalLength) * estimatedPageCount)));
};

// Large PDFs are split into overlapping chunks so relevant facts are not lost at chunk boundaries.
const chunkText = (text, { chunkSize = DEFAULT_CHUNK_SIZE, overlap = DEFAULT_CHUNK_OVERLAP } = {}) => {
  const cleanedText = normalizeWhitespace(text);
  const chunks = [];
  let start = 0;

  while (start < cleanedText.length) {
    const end = Math.min(cleanedText.length, start + chunkSize);
    const content = cleanedText.slice(start, end).trim();

    if (content.length > 100) {
      chunks.push({
        chunkId: `chunk_${String(chunks.length + 1).padStart(3, "0")}`,
        start,
        end,
        text: content,
        tokens: tokenize(content),
      });
    }

    if (end >= cleanedText.length) {
      break;
    }
    start = Math.max(0, end - overlap);
  }

  return chunks;
};

// This lightweight RAG score works without a vector database: keyword overlap + investor term boosts + numeric signals.
const scoreChunk = (chunk, queryTokens) => {
  const tokenSet = new Set(chunk.tokens);
  const matchedQueryTerms = queryTokens.filter((token) => tokenSet.has(token)).length;
  const importantTermHits = IMPORTANT_TERMS.filter((term) => tokenSet.has(term)).length;
  const numericSignal = /\b(?:rs\.?|lkr|million|billion|%|eps|profit|cash|assets|liabilities)\b/i.test(chunk.text) ? 0.25 : 0;

  return matchedQueryTerms + importantTermHits * 0.35 + numericSignal;
};

const buildSourceSnippet = (text) => {
  const snippet = normalizeWhitespace(text).slice(0, 420);
  return snippet.length === 420 ? `${snippet}...` : snippet;
};

const retrieveInvestorEvidence = (reportText, options = {}) => {
  const topK = Number(options.topK || process.env.REPORT_RAG_TOP_K || DEFAULT_TOP_K);
  const estimatedPageCount = options.estimatedPageCount || null;
  const chunks = chunkText(reportText, options);
  const scoredChunks = new Map();

  for (const query of INVESTOR_RETRIEVAL_QUERIES) {
    const queryTokens = tokenize(query);

    // Keep the two strongest passages per investor topic so one financial section
    // cannot crowd risk, governance, cash-flow, and outlook evidence out of the context.
    const queryResults = chunks
      .map((chunk) => ({ ...chunk, score: scoreChunk(chunk, queryTokens), matchedQuery: query }))
      .filter((chunk) => chunk.score > 0)
      .sort((first, second) => second.score - first.score)
      .slice(0, 2);

    for (const chunk of queryResults) {
      const score = chunk.score;

      const current = scoredChunks.get(chunk.chunkId);
      if (!current || score > current.score) {
        scoredChunks.set(chunk.chunkId, { ...chunk, score, matchedQuery: query });
      }
    }
  }

  // The final evidence set is capped to control model input size and processing cost.
  const selectedSources = [...scoredChunks.values()]
    .sort((first, second) => second.score - first.score)
    .slice(0, topK)
    .sort((first, second) => first.start - second.start)
    .map((chunk, index) => ({
      sourceId: `RAG-${index + 1}`,
      chunkId: chunk.chunkId,
      estimatedPage: estimatePageNumber(chunk.start, reportText.length, estimatedPageCount),
      score: Number(chunk.score.toFixed(3)),
      matchedQuery: chunk.matchedQuery,
      snippet: buildSourceSnippet(chunk.text),
      text: chunk.text,
    }));

  // The LLM receives only these retrieved evidence blocks before applying the selected Prompt 08.
  const context = selectedSources
    .map((source) => {
      const pageLabel = source.estimatedPage ? `estimated page ${source.estimatedPage}` : "page estimate unavailable";
      return `[${source.sourceId} | ${pageLabel} | ${source.chunkId}]\n${source.text}`;
    })
    .join("\n\n---\n\n");

  return {
    context,
    sources: selectedSources.map(({ text, ...source }) => source),
    validationSources: selectedSources.map(({ sourceId, estimatedPage, text }) => ({ sourceId, estimatedPage, text })),
    chunkCount: chunks.length,
    selectedCount: selectedSources.length,
  };
};

module.exports = {
  INVESTOR_RETRIEVAL_QUERIES,
  retrieveInvestorEvidence,
};
