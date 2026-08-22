# Code Walkthrough For Viva

## Main Idea

This component extracts investor-related information from annual report PDFs and converts it into structured, source-grounded outputs. It does not give buy, sell, or hold advice.

## What Happens When Generate Insight Is Clicked

1. The selected PDF is read from `data/annual_reports/`.
2. `src/pdf_extractor.py` extracts page-by-page text, tables, headings, page numbers, and source references.
3. `src/expected_output_builder.py` builds expected source-grounded values from the actual PDF text.
4. `src/run_prompt_benchmark.py` runs all 10 prompt strategies from `src/prompts.py`.
5. Each prompt output is saved separately in `data/prompt_outputs/{pdf_name}/`.
6. `src/evaluate_prompts.py` scores all prompt outputs using coverage, numeric accuracy, semantic similarity, source faithfulness, investor relevance, and hallucination penalty.
7. `src/select_best_prompt.py` selects one overall best prompt across the benchmark.
8. `src/generate_final_insight.py` uses that one selected best prompt to create the final investor report.

## Important Point About The Best Prompt

The system may show per-report rankings for analysis, but the final system selects one overall best prompt from the 10 prompts. That same selected prompt is used for every final report.

Current selected best prompt is stored in:

`data/evaluation_results/best_prompt_summary.json`

The exact prompt text to copy into the overall project is stored in:

`data/evaluation_results/best_prompt_to_use.txt`

The calculation explanation is stored in:

`data/evaluation_results/best_prompt_selection_report.md`

## How The Score Is Calculated

Each prompt output is compared against the expected output built from the PDF text.

The final score formula is:

`final_score = 0.25 * coverage_score + 0.20 * numeric_accuracy_score + 0.20 * semantic_similarity_score + 0.20 * source_faithfulness_score + 0.15 * investor_relevance_score - hallucination_penalty`

`coverage_score`
Checks how many expected investor fields were extracted.

`numeric_accuracy_score`
Checks whether numbers match even if formatting differs, such as million vs billion.

`similarity_score` / `semantic_similarity_score`
Compares expected output values with the 10 prompt output values using semantic similarity. If sentence-transformers is unavailable, TF-IDF cosine similarity is used.

`source_faithfulness_score`
Checks whether source quotes and page references actually exist in the extracted PDF text.

`investor_relevance_score`
Checks whether the output focuses on investor-useful information.

`hallucination_penalty`
Reduces the score when facts have no supporting evidence.

## Where To See The 10 Prompt Outputs

Open the dashboard and go to the `10 Prompt Outputs` tab. Select Prompt 01 to Prompt 10 from the dropdown.

The actual saved files are here:

`data/prompt_outputs/{pdf_name}/prompt_01.json`

through:

`data/prompt_outputs/{pdf_name}/prompt_10.json`

## Dashboard Tabs

`Final Report`
Shows the final investor-friendly output generated using the one overall selected best prompt.

`10 Prompt Outputs`
Shows the raw and parsed JSON outputs from Prompt 01 to Prompt 10.

`Scores`
Shows how each prompt scored. This is used to justify the selected best prompt.

`Evidence`
Shows source-grounded expected values with page references.

`Files`
Downloads JSON, CSV, and Markdown artifacts.

## Main Files To Explain

`src/config.py`
Defines folders and loads `.env` safely.

`src/pdf_extractor.py`
Extracts annual report text page by page.

`src/retrieval.py`
Finds relevant pages for investor fields.

`src/expected_output_builder.py`
Creates expected source-grounded answers.

`src/prompts.py`
Contains the 10 prompt strategies.

`src/llm_client.py`
Calls Azure OpenAI using environment variables only.

`src/run_prompt_benchmark.py`
Runs the 10 prompts and saves all outputs.

`src/evaluate_prompts.py`
Scores each prompt.

`src/select_best_prompt.py`
Chooses the one overall best prompt.

`src/generate_final_insight.py`
Creates the final investor-friendly report using the selected best prompt.

`app/streamlit_app.py`
Displays the UI.

## Disclaimer

The system is for investor education and annual report understanding only. This is not financial advice.
