# Methodology Summary

1. Annual report PDFs are extracted page-by-page with page references, detected tables, and section headings.
2. Investor-relevant fields are discovered using keyword and similarity-based retrieval over the extracted pages.
3. Expected outputs are built from source-grounded snippets with page-level evidence and missing-field flags.
4. Ten prompt strategies are benchmarked using the same retrieval context and a shared JSON output schema.
5. Prompt outputs are evaluated with coverage, numeric accuracy, semantic similarity, source faithfulness, hallucination penalty, and investor relevance.
6. The best prompt is selected using the final weighted score and used to produce a beginner-friendly investor insight report.