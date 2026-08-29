# Component 2: Financial Document Understanding and Language-Driven Insight Extraction

## 1. Problem Statement
Annual reports contain rich investor-relevant information, but most retail investors struggle to navigate large PDF disclosures, financial statement tables, risk notes, and governance sections. This component turns annual reports into structured, source-grounded investor-oriented insights without providing buy, sell, or hold advice.

## 2. Research Objective
Build a source-grounded annual report understanding pipeline that:
- extracts text and tables from local annual report PDFs
- discovers which investor-relevant fields exist in each report
- constructs expected outputs with page-level evidence
- benchmarks 10 prompt-engineering strategies on the same annual reports
- evaluates prompts with measurable research metrics
- selects the best prompt for final investor-friendly insight generation

### Application runtime
The integrated application accepts both annual and interim company reports. Before analysis, it verifies the selected company and requires the latest report period that should reasonably be available. The runtime extracts statement figures and operational highlights with page-level source quotes, including strengths, concerns, changes, and company milestones found in the uploaded report. A deterministic verified summary remains available when the optional wording service is disabled or unavailable.

## 3. Novelty
This component introduces a source-grounded prompt-engineering evaluation framework for investor-related information extraction from company annual reports. Unlike generic PDF summarization approaches, the framework first identifies investor-relevant information categories, constructs expected outputs with page-level evidence, evaluates 10 prompt strategies using coverage, numeric accuracy, semantic similarity, source faithfulness, and investor relevance, and selects the best prompt for final insight generation. This provides a measurable and reproducible approach for applying LLMs to financial document understanding in a localized emerging market context.

## 4. Related Work
Existing research includes:
1. Financial question answering over reports, such as FinQA.
2. Layout-aware document understanding, such as DocLLM.
3. Risk factor extraction from annual reports.
4. Forward-looking financial statement extraction from annual reports.
5. KPI extraction from annual reports using LLMs.

### Research Gap
Existing work commonly focuses on general financial QA, document layout understanding, risk extraction, or KPI extraction. This component focuses on localized investor-related annual report extraction for CSE-style company reports using prompt-engineering comparison and measurable source-grounded prompt selection.

## 5. Dataset / Annual Reports
Place annual report PDFs in:

```text
component_2/data/annual_reports/
```

The system automatically scans this folder.

## 6. Methodology
1. Extract page-level text, tables, headings, and source references from PDFs.
2. Discover investor-related categories and likely evidence pages using keyword and similarity retrieval.
3. Build expected source-grounded outputs from annual report text with page numbers and short snippets.
4. Run 10 prompt strategies using shared retrieval context and a common JSON schema.
5. Evaluate prompt outputs against expected evidence-backed results.
6. Select the best-performing prompt and generate final investor-friendly insights.

## 7. System Architecture

```text
annual_reports PDFs
  -> PDF extraction
  -> investor information discovery
  -> expected output construction
  -> 10-prompt benchmark
  -> prompt evaluation
  -> best prompt selection
  -> final investor insight generation
  -> Streamlit dashboard and export artifacts
```

## 8. Prompt Engineering Strategy
All 10 prompts use the same retrieval context and the same output schema so they can be compared scientifically. The prompt variations test role framing, schema strictness, evidence grounding, verification logic, ratio awareness, risk emphasis, beginner explanation quality, few-shot conditioning, and a hybrid best-practice approach.

## 9. The 10 Prompt Designs
1. Basic Extraction Prompt
2. Role-Based Financial Analyst Prompt
3. JSON Schema-Constrained Prompt
4. Source-Grounded Evidence Prompt
5. Chain-of-Verification Prompt
6. Ratio-Aware Prompt
7. Risk-Focused Investor Prompt
8. Beginner Investor Explanation Prompt
9. Few-Shot Prompt
10. Hybrid Best-Practice Prompt

## 10. Expected Output Construction
Expected outputs are saved under:

```text
data/expected_outputs/{pdf_name}_expected.json
```

Each field is grounded to extracted report text with:
- expected value
- source snippet
- page number
- confidence score
- not_found status when the report does not contain the field

## 11. Evaluation Metrics
The component evaluates each prompt using:
- Field Coverage Score
- Numeric Accuracy Score
- Semantic Similarity Score
- Source Faithfulness Score
- Investor Relevance Score
- Hallucination Penalty

## 12. Final Score Formula

```text
final_score =
  0.25 * coverage_score +
  0.20 * numeric_accuracy_score +
  0.20 * semantic_similarity_score +
  0.20 * source_faithfulness_score +
  0.15 * investor_relevance_score -
  hallucination_penalty
```

The final score is clamped between 0 and 1.

## 13. Results
Research-ready outputs are written to:
- `data/evaluation_results/research_prompt_comparison_table.csv`
- `data/evaluation_results/research_prompt_comparison_table.md`
- `data/evaluation_results/best_prompt_summary.json`
- `data/evaluation_results/novelty_statement.md`
- `data/evaluation_results/methodology_summary.md`

## 14. How to Run

### Setup

```bash
cd component_2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Use environment variables only. Do not hardcode Azure credentials.

On this machine, prefer `python` or `/opt/anaconda3/bin/python3` for the commands below. The `python3` command may point to an older framework Python that does not have the component dependencies installed.

### Commands

```bash
python src/extract_pdfs.py
python src/build_expected_outputs.py
python src/run_prompt_benchmark.py
python src/evaluate_prompts.py
python src/select_best_prompt.py
python src/generate_final_insight.py
python src/run_full_component.py
streamlit run app/streamlit_app.py
pytest
```

## 15. Limitations
- Some annual report fields may remain unavailable if the PDF text does not expose them clearly.
- OCR is not enabled by default; scanned PDFs trigger a warning instead.
- Table understanding is basic and may require enhancement for highly complex layouts.
- Expected output construction uses source-grounded heuristics and may still need manual review for research-grade gold labels.

## 16. Future Improvements
- Add OCR fallback for fully scanned annual reports.
- Improve table-to-structure extraction for statement line items.
- Add more advanced retrieval and layout-aware evidence ranking.
- Expand localized annual report coverage and human-validated gold datasets.
- Add error analysis dashboards for prompt failure modes.

## 17. Non-Advisory Disclaimer
This component is not a trading recommendation system. It is an investor education and insight extraction system. It does not provide buy, sell, or hold recommendations. This is not financial advice.

## Folder Structure

```text
component_2/
  data/
    annual_reports/
    extracted_text/
    expected_outputs/
    prompt_outputs/
    evaluation_results/
    final_insights/
  src/
  app/
  tests/
  README.md
  requirements.txt
  .env.example
```
