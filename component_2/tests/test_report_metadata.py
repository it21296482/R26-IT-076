from datetime import date

from src.report_metadata import (
    company_identity_matches,
    detect_report_metadata,
    validate_report_freshness,
)


def test_latest_interim_report_is_accepted():
    text = "John Keells Holdings PLC Interim Condensed Financial Statements Three Months Ended 30 June 2026"
    metadata = validate_report_freshness(detect_report_metadata(text), today=date(2026, 8, 30))
    assert metadata["report_type"] == "interim"
    assert metadata["reporting_period_end"] == "2026-06-30"
    assert metadata["is_latest"] is True


def test_old_annual_report_is_not_current():
    text = "Browns Investments PLC Annual Report for the year ended 31 March 2025"
    metadata = validate_report_freshness(detect_report_metadata(text), today=date(2026, 8, 30))
    assert metadata["report_type"] == "annual"
    assert metadata["latest_required_period_end"] == "2026-03-31"
    assert metadata["is_latest"] is False


def test_company_identity_rejects_another_company():
    assert company_identity_matches("Browns Investments PLC", "John Keells Holdings PLC", "JKH.N0000") is False
