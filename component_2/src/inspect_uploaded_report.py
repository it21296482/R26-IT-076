"""Fast pre-analysis validation for an uploaded annual or interim report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pymupdf as fitz

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.report_metadata import company_identity_matches, detect_report_metadata, validate_report_freshness
else:
    from .report_metadata import company_identity_matches, detect_report_metadata, validate_report_freshness


def inspect_report(pdf_path: Path, company_name: str, symbol: str) -> dict[str, object]:
    document = fitz.open(str(pdf_path))
    try:
        text = "\n".join(page.get_text("text") for page in list(document)[:8])
    finally:
        document.close()
    company_match = company_identity_matches(text, company_name, symbol)
    freshness = validate_report_freshness(detect_report_metadata(text))
    accepted = company_match and freshness["is_latest"] and freshness["report_type"] in {"annual", "interim"}
    if not company_match:
        message = f"Upload the latest financial report for {company_name}; this PDF belongs to a different company."
    elif freshness["report_type"] == "unknown" or not freshness["reporting_period_end"]:
        message = "The reporting period could not be verified. Upload the latest clearly labelled quarterly or annual report."
    elif not freshness["is_latest"]:
        required = freshness["latest_required_period_end"]
        article = "an" if freshness["report_type"] == "annual" else "a"
        message = f"This report is not the latest available period. Upload {article} {freshness['report_type']} report ending on or after {required}."
    else:
        message = f"Latest {freshness['report_type']} report verified for the period ended {freshness['reporting_period_end']}."
    return {**freshness, "company_match": company_match, "accepted": accepted, "message": message}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    try:
        result = inspect_report(args.pdf.resolve(), args.company_name, args.symbol.upper())
    except Exception as error:  # noqa: BLE001
        result = {"accepted": False, "message": f"The PDF could not be verified: {error}"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
