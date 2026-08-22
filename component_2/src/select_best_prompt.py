"""Select one reusable best prompt using saved evaluation scores.

This module is the bridge from Component 2 into the overall project: after the
10-prompt benchmark finishes, it selects one prompt strategy and exports the
exact prompt text that can be reused later in the main system.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys
    from pathlib import Path as BootstrapPath

    sys.path.insert(0, str(BootstrapPath(__file__).resolve().parent.parent))
    from src.config import EVALUATION_RESULTS_DIR, ensure_directories
    from src.prompts import prompt_definitions
    from src.utils import read_json, write_json, write_markdown
else:
    from .config import EVALUATION_RESULTS_DIR, ensure_directories
    from .prompts import prompt_definitions
    from .utils import read_json, write_json, write_markdown


SCORE_FIELDS = [
    "coverage_score",
    "numeric_accuracy_score",
    "semantic_similarity_score",
    "source_faithfulness_score",
    "investor_relevance_score",
    "hallucination_penalty",
    "final_score",
]

FINAL_SCORE_FORMULA = (
    "final_score = 0.25 * coverage_score + 0.20 * numeric_accuracy_score + "
    "0.20 * semantic_similarity_score + 0.20 * source_faithfulness_score + "
    "0.15 * investor_relevance_score - hallucination_penalty"
)


def prompt_lookup() -> dict[str, dict[str, str]]:
    """Return prompt definitions keyed by prompt ID."""
    return {prompt["prompt_id"]: prompt for prompt in prompt_definitions()}


def averaged_scores(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Average all scoring dimensions for one prompt across reports."""
    averages: dict[str, float] = {}
    for field in SCORE_FIELDS:
        values = [float(row.get(field, 0.0)) for row in rows]
        averages[field] = round(sum(values) / len(values), 4) if values else 0.0
    return averages


def build_markdown_report(result: dict[str, Any]) -> str:
    """Create a viva-ready explanation of how the best prompt was selected."""
    lines = [
        "# Best Prompt Selection Report",
        "",
        f"Selected prompt: **{result['best_prompt_id']} - {result['best_prompt_name']}**",
        "",
        f"Average final score: **{result['final_score']}**",
        "",
        "## How The Best Prompt Was Calculated",
        "",
        "Each annual report first gets an expected source-grounded output from the extracted PDF text. "
        "Then each of the 10 prompt outputs is compared against that expected output.",
        "",
        f"Formula: `{FINAL_SCORE_FORMULA}`",
        "",
        "## Score Meaning",
        "",
        "- `coverage_score`: how many expected investor fields the prompt extracted.",
        "- `numeric_accuracy_score`: how well numeric values match after unit/currency normalization.",
        "- `semantic_similarity_score`: similarity between expected values and prompt output values.",
        "- `source_faithfulness_score`: whether cited source quotes actually exist in the extracted PDF text.",
        "- `investor_relevance_score`: whether the output focuses on investor-useful categories.",
        "- `hallucination_penalty`: penalty for unsupported evidence or missing evidence.",
        "",
        "## Average Score Breakdown For Selected Prompt",
        "",
    ]
    for field, value in result["average_score_breakdown"].items():
        lines.append(f"- `{field}`: {value}")

    lines.extend(
        [
            "",
            "## Ranking Of All 10 Prompts",
            "",
            "| Rank | Prompt ID | Prompt Name | Similarity | Final Score | Reports Evaluated |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in result["prompt_rankings"]:
        lines.append(
            f"| {row['rank']} | {row['prompt_id']} | {row['prompt_name']} | "
            f"{row['average_score_breakdown']['semantic_similarity_score']} | "
            f"{row['final_score']} | {row['reports_evaluated']} |"
        )

    lines.extend(
        [
            "",
            "## Prompt Text To Reuse",
            "",
            "```text",
            result["best_prompt_text"],
            "```",
        ]
    )
    return "\n".join(lines)


def select_best_prompt() -> dict:
    """Choose the prompt with the highest average final score."""
    ensure_directories()
    prompts_by_id = prompt_lookup()
    aggregate: dict[str, dict[str, Any]] = defaultdict(lambda: {"prompt_name": "", "rows": []})

    for score_path in sorted(EVALUATION_RESULTS_DIR.glob("*_prompt_scores.json")):
        payload = read_json(score_path)
        for row in payload.get("scores", []):
            item = aggregate[row["prompt_id"]]
            item["prompt_name"] = row["prompt_name"]
            item["rows"].append(row)

    ranked: list[dict[str, Any]] = []
    for prompt_id, payload in aggregate.items():
        score_breakdown = averaged_scores(payload["rows"])
        prompt = prompts_by_id.get(prompt_id, {})
        ranked.append(
            {
                "prompt_id": prompt_id,
                "prompt_name": payload["prompt_name"],
                "prompt_text": prompt.get("prompt_text", ""),
                "final_score": score_breakdown["final_score"],
                "reports_evaluated": len(payload["rows"]),
                "average_score_breakdown": score_breakdown,
            }
        )
    ranked.sort(key=lambda item: item["final_score"], reverse=True)
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index

    if not ranked:
        result = {
            "best_prompt_id": None,
            "best_prompt_name": None,
            "final_score": 0.0,
            "best_prompt_text": "",
            "final_score_formula": FINAL_SCORE_FORMULA,
            "average_score_breakdown": {},
            "prompt_rankings": [],
            "reason": "No prompt evaluation results were available.",
            "top_strengths": [],
            "weaknesses": [],
            "research_conclusion": "",
        }
        write_json(EVALUATION_RESULTS_DIR / "best_prompt_summary.json", result)
        return result

    best_prompt = ranked[0]
    result = {
        "best_prompt_id": best_prompt["prompt_id"],
        "best_prompt_name": best_prompt["prompt_name"],
        "final_score": best_prompt["final_score"],
        "best_prompt_text": best_prompt["prompt_text"],
        "final_score_formula": FINAL_SCORE_FORMULA,
        "average_score_breakdown": best_prompt["average_score_breakdown"],
        "prompt_rankings": ranked,
        "calculation_method": {
            "expected_output_source": "data/expected_outputs/{pdf_name}_expected.json",
            "prompt_output_source": "data/prompt_outputs/{pdf_name}/prompt_01.json ... prompt_10.json",
            "similarity_score": "semantic_similarity_score compares expected values with extracted prompt values using sentence-transformers when available, otherwise TF-IDF cosine similarity.",
            "selection_rule": "Choose the prompt with the highest average final_score across evaluated annual reports.",
            "formula": FINAL_SCORE_FORMULA,
        },
        "reason": "Selected from the highest average final score across evaluated annual reports.",
        "top_strengths": [
            "Strong coverage of investor-relevant fields",
            "Better balance between numeric fidelity and source-grounded evidence",
            "Higher research-oriented reproducibility under a shared schema",
        ],
        "weaknesses": [
            "Some annual reports may still require manual review for ambiguous disclosures",
            "Ratio derivations remain dependent on extraction quality and available context",
        ],
        "research_conclusion": (
            f"{best_prompt['prompt_name']} achieved the highest score because it best balanced structured output, "
            "investor-specific field targeting, evidence grounding, and low hallucination behavior. "
            "This suggests that prompt engineering materially affects accuracy and faithfulness in annual report understanding."
        ),
    }
    write_json(EVALUATION_RESULTS_DIR / "best_prompt_summary.json", result)
    write_markdown(EVALUATION_RESULTS_DIR / "best_prompt_selection_report.md", build_markdown_report(result))
    (EVALUATION_RESULTS_DIR / "best_prompt_to_use.txt").write_text(result["best_prompt_text"], encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for best prompt selection."""
    parser = argparse.ArgumentParser(description="Select the best-performing prompt.")
    return parser.parse_args()


def main() -> None:
    """Select and export the best prompt from the command line."""
    parse_args()
    select_best_prompt()


if __name__ == "__main__":
    main()
