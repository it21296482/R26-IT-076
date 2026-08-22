"""CLI entry point for running the complete Component 2 pipeline."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.build_expected_outputs import main as build_expected_outputs_main
    from src.config import ensure_directories
    from src.evaluate_prompts import evaluate_all_prompts
    from src.extract_pdfs import main as extract_pdfs_main
    from src.generate_final_insight import generate_final_insights
    from src.run_prompt_benchmark import run_benchmark
    from src.select_best_prompt import select_best_prompt
else:
    from .build_expected_outputs import main as build_expected_outputs_main
    from .config import ensure_directories
    from .evaluate_prompts import evaluate_all_prompts
    from .extract_pdfs import main as extract_pdfs_main
    from .generate_final_insight import generate_final_insights
    from .run_prompt_benchmark import run_benchmark
    from .select_best_prompt import select_best_prompt


def main() -> None:
    """Run extraction, expected output building, prompts, scoring, and final reports."""
    ensure_directories()
    extract_pdfs_main()
    build_expected_outputs_main()
    run_benchmark()
    evaluate_all_prompts()
    select_best_prompt()
    generate_final_insights()


if __name__ == "__main__":
    main()
