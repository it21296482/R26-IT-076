"""Create the final investor-friendly report from the best prompt output.

This module does not call the LLM again. It reads saved prompt benchmark
outputs, uses the single overall best prompt selected from the benchmark, and
writes the final JSON/Markdown files that the dashboard displays.
"""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in {None, ""}:
    import sys
    from pathlib import Path as BootstrapPath

    sys.path.insert(0, str(BootstrapPath(__file__).resolve().parent.parent))
    from src.config import FINAL_INSIGHTS_DIR, PROMPT_OUTPUTS_DIR, EVALUATION_RESULTS_DIR, ensure_directories
    from src.utils import read_json, slugify, write_json, write_markdown
else:
    from .config import FINAL_INSIGHTS_DIR, PROMPT_OUTPUTS_DIR, EVALUATION_RESULTS_DIR, ensure_directories
    from .utils import read_json, slugify, write_json, write_markdown


def build_markdown_report(prompt_output: dict) -> str:
    """Convert the selected prompt JSON into a readable Markdown report."""
    parsed = prompt_output["parsed_json"]
    facts = parsed["extracted_facts"]
    insight = parsed["investor_friendly_insight"]
    lines = [
        f"# {parsed['metadata'].get('company_name') or parsed['metadata'].get('pdf_name')}",
        "",
        f"Reporting year: {parsed['metadata'].get('reporting_year') or 'Not available'}",
        "",
        "## Key Financial Indicators",
        "",
    ]
    for section in ["financial_performance", "financial_position", "cash_flow", "investor_ratios"]:
        lines.append(f"### {section.replace('_', ' ').title()}")
        for field, value in facts.get(section, {}).items():
            lines.append(f"- {field.replace('_', ' ').title()}: {value if value is not None else 'Not found'}")
        lines.append("")

    for section in ["shareholder_information", "risk_factors", "management_governance", "future_outlook"]:
        lines.append(f"### {section.replace('_', ' ').title()}")
        for field, value in facts.get(section, {}).items():
            lines.append(f"- {field.replace('_', ' ').title()}: {value if value is not None else 'Not found'}")
        lines.append("")

    lines.extend(
        [
            "## Beginner-Friendly Explanation",
            "",
            insight.get("summary", ""),
            "",
            "### Key Strengths",
            *[f"- {item}" for item in insight.get("key_strengths", [])],
            "",
            "### Key Concerns",
            *[f"- {item}" for item in insight.get("key_concerns", [])],
            "",
            "### Risk Level Explanation",
            insight.get("risk_level_explanation", ""),
            "",
            "## Source References",
            "",
        ]
    )
    for evidence in parsed.get("source_evidence", []):
        if isinstance(evidence, dict):
            lines.append(
                f"- {evidence.get('field')}: {evidence.get('value')} (page {evidence.get('page_number')}) "
                f"quote: {evidence.get('source_quote')}"
            )
        else:
            lines.append(f"- {evidence}")
    lines.extend(["", "## Disclaimer", "", "This is not financial advice."])
    return "\n".join(lines)


def selected_best_prompt_id() -> str | None:
    """Return the one overall best prompt selected for the whole system.

    Per-report score files may have their own rank 1 prompt, but the project
    needs one final prompt choice. That global choice is stored in
    data/evaluation_results/best_prompt_summary.json.
    """
    best_prompt_path = EVALUATION_RESULTS_DIR / "best_prompt_summary.json"
    if best_prompt_path.exists():
        return read_json(best_prompt_path).get("best_prompt_id")
    return None


def generate_final_insight_for_pdf(pdf_stem: str) -> list[Path]:
    """Generate final JSON and Markdown files using the global best prompt."""
    ensure_directories()
    normalized_stem = slugify(pdf_stem)
    best_prompt_id = selected_best_prompt_id()
    if not best_prompt_id:
        return []

    prompt_output_path = PROMPT_OUTPUTS_DIR / normalized_stem / f"{best_prompt_id}.json"
    if not prompt_output_path.exists():
        return []

    prompt_output = read_json(prompt_output_path)
    if not prompt_output.get("parsed_json"):
        return []

    json_output_path = FINAL_INSIGHTS_DIR / f"{normalized_stem}_final_investor_insight.json"
    md_output_path = FINAL_INSIGHTS_DIR / f"{normalized_stem}_final_investor_insight.md"
    write_json(json_output_path, prompt_output["parsed_json"])
    write_markdown(md_output_path, build_markdown_report(prompt_output))
    return [json_output_path, md_output_path]


def generate_final_insights() -> list[Path]:
    """Generate final reports for every report that has prompt outputs."""
    ensure_directories()
    outputs: list[Path] = []
    for prompt_dir in sorted(PROMPT_OUTPUTS_DIR.iterdir()):
        if not prompt_dir.is_dir():
            continue
        outputs.extend(generate_final_insight_for_pdf(prompt_dir.name))
    return outputs


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for final insight generation."""
    parser = argparse.ArgumentParser(description="Generate final investor insights with the best prompt.")
    return parser.parse_args()


def main() -> None:
    """Generate final insights from the command line."""
    parse_args()
    generate_final_insights()


if __name__ == "__main__":
    main()
