# News and Sentiment Research Package

## Preserved source

`original/` is a clean copy of the available news and sentiment research work.
It preserves collectors, source configuration, language-processing utilities,
training/evaluation data, model files, and research scripts. Nested Git metadata,
installed dependencies, uploads, and `.env` secrets are intentionally excluded.

## Application integration

The production-facing news and sentiment adapter is:

`server/src/services/externalContextService.js`

It integrates the useful research ideas while adding failure-aware behavior:

- selected-company and Sri Lankan market news queries;
- dated source URLs, source names, relevance scope, and event categories;
- transparent finance-language sentiment labels;
- duplicate removal;
- explicit source warnings and a causal-language warning.

Gold, Oil, VIX, USD/LKR, ASPI comparison, and quantitative factor relationships
are not claimed by this contribution. They are collected as external-market risk
context for Component 4.

## Verification

Pure behavior tests are located in:

`server/test/externalContextService.test.js`

Run them with:

```bash
cd server
npm test
```

The current automated tests verify sentiment wording, event categories,
deduplication, source-failure handling, and non-causal interpretation. Shared
service tests also verify the separately exposed market-factor calculations.

## Research limitations

- The available proposal does not isolate a sufficiently specific individual
  novelty and largely repeats the overall group-system scope.
- The preserved classifier and rules still require a manually labelled,
  CSE-oriented holdout evaluation reporting precision, recall, F1, class support,
  freshness, and company-relevance error.
- News search cannot guarantee collection of every possible article.
- Provider symbols and source availability can change and must be monitored.
