"""CLI entry point for building expected source-grounded outputs."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.config import EXTRACTED_TEXT_DIR, ensure_directories
    from src.expected_output_builder import build_all_expected_outputs
    from src.pdf_extractor import extract_all_pdfs
else:
    from .config import EXTRACTED_TEXT_DIR, ensure_directories
    from .expected_output_builder import build_all_expected_outputs
    from .pdf_extractor import extract_all_pdfs


def main() -> None:
    """Build expected outputs, extracting PDFs first if needed."""
    ensure_directories()
    if not list(EXTRACTED_TEXT_DIR.glob("*_pages.json")):
        extract_all_pdfs()
    build_all_expected_outputs()


if __name__ == "__main__":
    main()
