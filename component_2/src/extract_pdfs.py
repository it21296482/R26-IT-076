"""CLI entry point for extracting annual report PDFs."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.config import ensure_directories
    from src.pdf_extractor import extract_all_pdfs
else:
    from .config import ensure_directories
    from .pdf_extractor import extract_all_pdfs


def main() -> None:
    """Extract all PDFs in data/annual_reports."""
    ensure_directories()
    outputs = extract_all_pdfs()
    if not outputs:
        print("No PDFs found in data/annual_reports. Add annual report PDFs there before extraction.")


if __name__ == "__main__":
    main()
