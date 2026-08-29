"""Run Prompt 01 through Prompt 10 for annual report PDFs.

Each prompt output is saved separately under data/prompt_outputs/{pdf}/ so the
dashboard can show the result of all ten prompt strategies.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    import sys
    from pathlib import Path as BootstrapPath

    sys.path.insert(0, str(BootstrapPath(__file__).resolve().parent.parent))
    from src.config import EXTRACTED_TEXT_DIR, PROMPT_OUTPUTS_DIR, ensure_directories
    from src.expected_output_builder import build_all_expected_outputs
    from src.llm_client import LLMClient
    from src.normalization import collect_missing_fields, normalize_prompt_json
    from src.pdf_extractor import extract_all_pdfs
    from src.prompts import prompt_definitions
    from src.retrieval import build_retrieval_context
    from src.utils import read_json, slugify, write_json
else:
    from .config import EXTRACTED_TEXT_DIR, PROMPT_OUTPUTS_DIR, ensure_directories
    from .expected_output_builder import build_all_expected_outputs
    from .llm_client import LLMClient
    from .normalization import collect_missing_fields, normalize_prompt_json
    from .pdf_extractor import extract_all_pdfs
    from .prompts import prompt_definitions
    from .retrieval import build_retrieval_context
    from .utils import read_json, slugify, write_json


def build_prompt_input(prompt_text: str, extracted_payload: dict) -> str:
    """Combine a prompt template with the selected report context."""
    retrieval_context = build_retrieval_context(extracted_payload)
    return (
        f"{prompt_text}\n\n"
        f"PDF Name: {extracted_payload['pdf_name']}\n"
        f"Context:\n{retrieval_context}\n"
    )


def output_is_complete(output_path: Path) -> bool:
    """Check whether a prompt output file is valid enough to skip rerunning."""
    if not output_path.exists():
        return False
    try:
        payload = read_json(output_path)
    except Exception:
        return False
    return payload.get("parsed_json") is not None and payload.get("errors") is None


def run_benchmark_for_pdf(extracted_json_path: Path, llm_client: LLMClient | None = None, force: bool = False) -> list[Path]:
    """Run all ten prompt strategies for one extracted report."""
    extracted_payload = read_json(extracted_json_path)
    output_dir = PROMPT_OUTPUTS_DIR / slugify(extracted_payload["pdf_stem"])
    output_dir.mkdir(parents=True, exist_ok=True)

    client = llm_client or LLMClient()
    outputs: list[Path] = []

    for prompt in prompt_definitions():
        output_path = output_dir / f"{prompt['prompt_id']}.json"
        if not force and output_is_complete(output_path):
            print(f"Skipping {extracted_payload['pdf_name']} {prompt['prompt_id']} because output already exists.")
            outputs.append(output_path)
            continue

        print(f"Running {extracted_payload['pdf_name']} {prompt['prompt_id']} - {prompt['prompt_name']}...")
        prompt_input = build_prompt_input(prompt["prompt_text"], extracted_payload)
        llm_result = client.run_json_prompt(prompt_input)
        normalized = None
        if llm_result["parsed_output"] is not None:
            normalized = normalize_prompt_json(
                llm_result["parsed_output"],
                extracted_payload["pdf_name"],
                prompt["prompt_id"],
                client.deployment,
            )
            collect_missing_fields(normalized)

        payload = {
            "pdf_name": extracted_payload["pdf_name"],
            "prompt_id": prompt["prompt_id"],
            "prompt_name": prompt["prompt_name"],
            "model": client.deployment,
            "full_model_output": llm_result["raw_output"],
            "parsed_json": normalized,
            "token_usage": llm_result["usage"],
            "runtime_seconds": llm_result["runtime_seconds"],
            "errors": llm_result["error"],
        }
        write_json(output_path, payload)
        print(f"Saved {output_path}")
        outputs.append(output_path)
    return outputs


def select_extracted_paths(report_name: str | None = None) -> list[Path]:
    """Return extracted JSON files for all reports or one requested report."""
    extracted_paths = sorted(EXTRACTED_TEXT_DIR.glob("*_pages.json"))
    if report_name is None:
        return extracted_paths
    report_stem = slugify(Path(report_name).stem)
    return [path for path in extracted_paths if path.name == f"{report_stem}_pages.json"]


def run_benchmark(report_name: str | None = None, force: bool = False) -> list[Path]:
    """Run the prompt benchmark, reusing already completed outputs."""
    ensure_directories()
    if not list(EXTRACTED_TEXT_DIR.glob("*_pages.json")):
        extract_all_pdfs()
    build_all_expected_outputs()

    extracted_paths = select_extracted_paths(report_name)
    if not extracted_paths:
        print("No matching extracted annual reports found. Place PDFs in data/annual_reports and run extract_pdfs.py first.")
        return []

    outputs: list[Path] = []
    client = LLMClient()
    for extracted_json_path in extracted_paths:
        outputs.extend(run_benchmark_for_pdf(extracted_json_path, client, force=force))
    return outputs


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for running the benchmark."""
    parser = argparse.ArgumentParser(description="Run the 10-prompt benchmark on extracted annual reports.")
    parser.add_argument("--report", help="Run one report only, for example DIAL_2024.pdf")
    parser.add_argument("--force", action="store_true", help="Re-run prompts even when output files already exist.")
    return parser.parse_args()


def main() -> None:
    """Run the prompt benchmark from the command line."""
    args = parse_args()
    run_benchmark(report_name=args.report, force=args.force)


if __name__ == "__main__":
    main()
