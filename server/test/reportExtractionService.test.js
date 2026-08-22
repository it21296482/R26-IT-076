const assert = require("node:assert/strict");
const test = require("node:test");
const {
  isStandardOpenAIKey,
  normalizeExtractionShape,
  validateSourceEvidence,
} = require("../src/services/reportExtractionService");

const validationSources = [
  {
    sourceId: "RAG-1",
    estimatedPage: 4,
    text: "Revenue increased to Rs. 10 million during the year.",
  },
];

test("normalizes Prompt 08 output to the complete research schema", () => {
  const output = normalizeExtractionShape(
    {
      metadata: { company_name: "Test PLC" },
      extracted_facts: { financial_performance: { revenue_turnover: "Rs. 10 million" } },
      investor_friendly_insight: { summary: "Simple summary", key_strengths: ["Revenue"], key_concerns: [] },
      confidence_score: 1.7,
    },
    { pdfName: "test.pdf", model: "test-model" },
    validationSources
  );

  assert.equal(output.metadata.prompt_id, "prompt_08");
  assert.equal(output.extracted_facts.financial_performance.revenue_turnover, "Rs. 10 million");
  assert.equal(output.extracted_facts.financial_performance.net_finance_cost, null);
  assert.equal(output.confidence_score, 1);
  assert.ok(output.missing_fields.includes("financial_performance.profit_after_tax"));
});

test("keeps only evidence quotes found in their declared RAG source", () => {
  const evidence = validateSourceEvidence(
    [
      {
        field: "revenue_turnover",
        value: "Rs. 10 million",
        source_id: "RAG-1",
        source_quote: "Revenue increased to Rs. 10 million during the year.",
      },
      {
        field: "profit_after_tax",
        value: "invented",
        source_id: "RAG-1",
        source_quote: "Profit was Rs. 99 million.",
      },
    ],
    validationSources
  );

  assert.equal(evidence.length, 1);
  assert.equal(evidence[0].field, "revenue_turnover");
  assert.equal(evidence[0].page_number, 4);
});

test("recognizes only standard OpenAI key formats for the OpenAI provider", () => {
  assert.equal(isStandardOpenAIKey("sk-proj-example_key"), true);
  assert.equal(isStandardOpenAIKey("18GRdCGjAzureStyleKey"), false);
  assert.equal(isStandardOpenAIKey("replace_this_key"), false);
});
