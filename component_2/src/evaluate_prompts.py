"""Score prompt outputs against expected source-grounded results.

The evaluator calculates coverage, numeric accuracy, semantic similarity,
source faithfulness, investor relevance, and hallucination penalty.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

if __package__ in {None, ""}:
    import sys
    from pathlib import Path as BootstrapPath

    sys.path.insert(0, str(BootstrapPath(__file__).resolve().parent.parent))
    from src.config import EVALUATION_RESULTS_DIR, EXPECTED_OUTPUTS_DIR, EXTRACTED_TEXT_DIR, PROMPT_OUTPUTS_DIR, ensure_directories
    from src.normalization import flatten_prompt_fields
    from src.schemas import INVESTOR_FIELD_GROUPS
    from src.utils import clamp, flatten_text, has_meaningful_value, read_json, similar_numeric, slugify, tokenize_text, write_json, write_markdown
else:
    from .config import EVALUATION_RESULTS_DIR, EXPECTED_OUTPUTS_DIR, EXTRACTED_TEXT_DIR, PROMPT_OUTPUTS_DIR, ensure_directories
    from .normalization import flatten_prompt_fields
    from .schemas import INVESTOR_FIELD_GROUPS
    from .utils import clamp, flatten_text, has_meaningful_value, read_json, similar_numeric, slugify, tokenize_text, write_json, write_markdown


def expected_output_paths() -> list[Path]:
    """Find all expected-output files that should be used for evaluation."""
    return sorted(EXPECTED_OUTPUTS_DIR.glob("*_expected.json"))


def sentence_similarity(expected: str, predicted: str) -> float:
    """Compare two text values with embeddings, falling back to TF-IDF."""
    if not expected.strip() or not predicted.strip():
        return 0.0
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode([expected, predicted])
        numerator = float((embeddings[0] * embeddings[1]).sum())
        denominator = float((embeddings[0] ** 2).sum() ** 0.5 * (embeddings[1] ** 2).sum() ** 0.5)
        return numerator / denominator if denominator else 0.0
    except Exception:
        try:
            vectorizer = TfidfVectorizer()
            matrix = vectorizer.fit_transform([expected, predicted])
            return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
        except ValueError:
            return 0.0


def flattened_expected_fields(expected_payload: dict[str, Any]) -> OrderedDict[str, Any]:
    """Return expected fields as an ordered mapping."""
    return OrderedDict(expected_payload.get("expected_outputs", {}))


def validate_source_quote(extracted_payload: dict[str, Any], page_number: int | str, quote: str) -> bool:
    """Check that a cited quote actually appears on the cited PDF page."""
    if not quote or page_number in (None, ""):
        return False
    try:
        page_number_int = int(page_number)
    except Exception:
        return False
    for page in extracted_payload.get("pages", []):
        if page.get("page_number") == page_number_int:
            return quote.strip() in page.get("text", "")
    return False


def coverage_score(expected_fields: OrderedDict[str, Any], extracted_fields: OrderedDict[str, Any]) -> float:
    """Measure how many expected fields the prompt extracted."""
    expected_names = [field for field, payload in expected_fields.items() if payload.get("expected_value") is not None]
    if not expected_names:
        return 0.0
    extracted_count = sum(1 for field in expected_names if has_meaningful_value(extracted_fields.get(field)))
    return extracted_count / len(expected_names)


def numeric_accuracy_score(expected_fields: OrderedDict[str, Any], extracted_fields: OrderedDict[str, Any]) -> float:
    """Compare numeric values after normalization of currency/units."""
    scores = []
    for category_fields in INVESTOR_FIELD_GROUPS.values():
        for field_name, metadata in category_fields.items():
            if not metadata.get("numeric"):
                continue
            expected_value = expected_fields.get(field_name, {}).get("expected_value")
            extracted_value = extracted_fields.get(field_name)
            if expected_value is None:
                continue
            scores.append(similar_numeric(expected_value, extracted_value))
    return sum(scores) / len(scores) if scores else 0.0


def semantic_similarity_score(expected_fields: OrderedDict[str, Any], extracted_fields: OrderedDict[str, Any]) -> float:
    """Measure text similarity between expected and extracted values."""
    scores = []
    for field_name, payload in expected_fields.items():
        expected_value = payload.get("expected_value")
        extracted_value = extracted_fields.get(field_name)
        if expected_value is None or not has_meaningful_value(extracted_value):
            continue
        expected_text = flatten_text(expected_value)
        extracted_text = flatten_text(extracted_value)
        if not expected_text or not extracted_text:
            continue
        scores.append(sentence_similarity(expected_text, extracted_text))
    return sum(scores) / len(scores) if scores else 0.0


def source_faithfulness_score(prompt_output: dict[str, Any], extracted_payload: dict[str, Any]) -> float:
    """Reward outputs whose source quotes exist in the extracted report text."""
    evidence = prompt_output.get("source_evidence", []) if prompt_output else []
    if not evidence:
        return 0.0
    valid = 0
    for item in evidence:
        if not isinstance(item, dict):
            continue
        if validate_source_quote(extracted_payload, item.get("page_number"), item.get("source_quote", "")):
            valid += 1
    return valid / len(evidence)


def hallucination_penalty(prompt_output: dict[str, Any], extracted_payload: dict[str, Any]) -> float:
    """Penalize unsupported or invalid evidence."""
    evidence = prompt_output.get("source_evidence", []) if prompt_output else []
    if not evidence:
        return 0.15
    invalid = 0
    for item in evidence:
        if not isinstance(item, dict):
            invalid += 1
            continue
        if not validate_source_quote(extracted_payload, item.get("page_number"), item.get("source_quote", "")):
            invalid += 1
    return min(0.25, invalid / max(1, len(evidence)) * 0.25)


def investor_relevance_score(prompt_output: dict[str, Any]) -> float:
    """Reward outputs that cover investor-useful categories and disclaimers."""
    if not prompt_output:
        return 0.0
    extracted_facts = prompt_output.get("extracted_facts", {})
    coverage_points = 0
    total_categories = len(INVESTOR_FIELD_GROUPS)
    for category in INVESTOR_FIELD_GROUPS:
        values = extracted_facts.get(category, {})
        if any(has_meaningful_value(value) for value in values.values()):
            coverage_points += 1
    note = prompt_output.get("investor_friendly_insight", {}).get("non_advisory_note", "")
    summary = prompt_output.get("investor_friendly_insight", {}).get("summary", "")
    bonus = 0.15 if "not financial advice" in note.lower() else 0.0
    bonus += 0.1 if len(summary.strip()) > 40 else 0.0
    return clamp((coverage_points / total_categories) * 0.75 + bonus)


def evaluate_pdf(pdf_stem: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Evaluate all prompt outputs for one PDF."""
    expected_payload = read_json(EXPECTED_OUTPUTS_DIR / f"{slugify(pdf_stem)}_expected.json")
    extracted_payload = read_json(EXTRACTED_TEXT_DIR / f"{slugify(pdf_stem)}_pages.json")
    prompt_output_dir = PROMPT_OUTPUTS_DIR / slugify(pdf_stem)
    expected_fields = flattened_expected_fields(expected_payload)

    rows: list[dict[str, Any]] = []

    for prompt_output_path in sorted(prompt_output_dir.glob("prompt_*.json")):
        prompt_payload = read_json(prompt_output_path)
        parsed_json = prompt_payload.get("parsed_json")
        extracted_fields = flatten_prompt_fields(parsed_json) if parsed_json else OrderedDict()
        score_coverage = coverage_score(expected_fields, extracted_fields)
        score_numeric = numeric_accuracy_score(expected_fields, extracted_fields)
        score_semantic = semantic_similarity_score(expected_fields, extracted_fields)
        score_faithfulness = source_faithfulness_score(parsed_json or {}, extracted_payload)
        score_relevance = investor_relevance_score(parsed_json or {})
        penalty = hallucination_penalty(parsed_json or {}, extracted_payload)

        final_score = clamp(
            0.25 * score_coverage
            + 0.20 * score_numeric
            + 0.20 * score_semantic
            + 0.20 * score_faithfulness
            + 0.15 * score_relevance
            - penalty
        )

        rows.append(
            {
                "pdf_name": expected_payload["pdf_name"],
                "prompt_id": prompt_payload["prompt_id"],
                "prompt_name": prompt_payload["prompt_name"],
                "coverage_score": round(score_coverage, 4),
                "numeric_accuracy_score": round(score_numeric, 4),
                "similarity_score": round(score_semantic, 4),
                "semantic_similarity_score": round(score_semantic, 4),
                "source_faithfulness_score": round(score_faithfulness, 4),
                "investor_relevance_score": round(score_relevance, 4),
                "hallucination_penalty": round(penalty, 4),
                "final_score": round(final_score, 4),
            }
        )

    rows.sort(key=lambda item: item["final_score"], reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    summary = {
        "pdf_name": expected_payload["pdf_name"],
        "best_prompt_id": rows[0]["prompt_id"] if rows else None,
        "best_prompt_name": rows[0]["prompt_name"] if rows else None,
        "scores": rows,
    }
    return rows, summary


def save_evaluation_artifacts(rows: list[dict[str, Any]], summary: dict[str, Any], pdf_stem: str) -> None:
    """Save prompt scores to CSV and JSON."""
    csv_path = EVALUATION_RESULTS_DIR / f"{slugify(pdf_stem)}_prompt_scores.csv"
    json_path = EVALUATION_RESULTS_DIR / f"{slugify(pdf_stem)}_prompt_scores.json"
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    write_json(json_path, summary)


def build_research_tables(all_rows: list[dict[str, Any]]) -> None:
    """Create combined score tables across reports."""
    csv_path = EVALUATION_RESULTS_DIR / "research_prompt_comparison_table.csv"
    md_path = EVALUATION_RESULTS_DIR / "research_prompt_comparison_table.md"
    if all_rows:
        with csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)

        lines = [
            "| PDF | Prompt ID | Prompt Name | Coverage | Numeric | Semantic | Faithfulness | Relevance | Penalty | Final | Rank |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in all_rows:
            lines.append(
                f"| {row['pdf_name']} | {row['prompt_id']} | {row['prompt_name']} | {row['coverage_score']:.4f} | "
                f"{row['numeric_accuracy_score']:.4f} | {row['semantic_similarity_score']:.4f} | "
                f"{row['source_faithfulness_score']:.4f} | {row['investor_relevance_score']:.4f} | "
                f"{row['hallucination_penalty']:.4f} | {row['final_score']:.4f} | {row['rank']} |"
            )
        write_markdown(md_path, "\n".join(lines))


def write_methodology_files() -> None:
    """Write methodology artifacts used for research documentation."""
    write_markdown(
        EVALUATION_RESULTS_DIR / "novelty_statement.md",
        "This component introduces a source-grounded prompt-engineering evaluation framework for investor-related information extraction from company annual reports. Unlike generic PDF summarization approaches, the framework first identifies investor-relevant information categories, constructs expected outputs with page-level evidence, evaluates 10 prompt strategies using coverage, numeric accuracy, semantic similarity, source faithfulness, and investor relevance, and selects the best prompt for final insight generation. This provides a measurable and reproducible approach for applying LLMs to financial document understanding in a localized emerging market context.\n",
    )
    write_markdown(
        EVALUATION_RESULTS_DIR / "methodology_summary.md",
        "\n".join(
            [
                "# Methodology Summary",
                "",
                "1. Annual report PDFs are extracted page-by-page with page references, detected tables, and section headings.",
                "2. Investor-relevant fields are discovered using keyword and similarity-based retrieval over the extracted pages.",
                "3. Expected outputs are built from source-grounded snippets with page-level evidence and missing-field flags.",
                "4. Ten prompt strategies are benchmarked using the same retrieval context and a shared JSON output schema.",
                "5. Prompt outputs are evaluated with coverage, numeric accuracy, semantic similarity, source faithfulness, hallucination penalty, and investor relevance.",
                "6. The best prompt is selected using the final weighted score and used to produce a beginner-friendly investor insight report.",
            ]
        ),
    )


def evaluate_all_prompts() -> list[dict[str, Any]]:
    """Evaluate every report that has an expected output file."""
    ensure_directories()
    all_rows: list[dict[str, Any]] = []
    for expected_path in expected_output_paths():
        pdf_stem = expected_path.name.replace("_expected.json", "")
        rows, summary = evaluate_pdf(pdf_stem)
        save_evaluation_artifacts(rows, summary, pdf_stem)
        all_rows.extend(rows)
    build_research_tables(all_rows)
    write_methodology_files()
    return all_rows


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for prompt evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate prompt outputs against expected source-grounded results.")
    return parser.parse_args()


def main() -> None:
    """Run prompt evaluation from the command line."""
    parse_args()
    evaluate_all_prompts()


if __name__ == "__main__":
    main()
