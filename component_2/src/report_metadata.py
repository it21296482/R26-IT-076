"""Detect report identity, type, period, and freshness from extracted PDF text."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any


GENERIC_COMPANY_WORDS = {"company", "holdings", "limited", "ltd", "plc", "group", "the"}
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
DATE_PATTERN = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{4})",
    flags=re.IGNORECASE,
)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def company_identity_matches(text: str, company_name: str, symbol: str) -> bool:
    normalized = normalize_text(text)
    company_phrase = normalize_text(company_name)
    if company_phrase and company_phrase in normalized:
        return True
    distinctive_tokens = [
        token for token in re.findall(r"[a-z0-9]+", company_phrase)
        if len(token) >= 4 and token not in GENERIC_COMPANY_WORDS
    ]
    if distinctive_tokens and all(token in normalized for token in distinctive_tokens):
        return True
    ticker = normalize_text(symbol).split(".")[0]
    return len(ticker) >= 3 and re.search(rf"\b{re.escape(ticker)}\b", normalized) is not None


def _parsed_dates(text: str) -> list[date]:
    values: list[date] = []
    for match in DATE_PATTERN.finditer(text):
        try:
            values.append(date(int(match.group(3)), MONTHS[match.group(2).lower()], int(match.group(1))))
        except ValueError:
            continue
    return values


def detect_report_metadata(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    annual = "annual report" in normalized or "year ended" in normalized
    interim = any(term in normalized for term in (
        "interim", "quarter ended", "three months ended", "six months ended", "nine months ended",
    ))
    report_type = "annual" if annual and not interim else "interim" if interim else "unknown"

    period_candidates: list[date] = []
    for phrase in re.finditer(
        r"(?:period|year|quarter|three months|six months|nine months)\s+ended\s+[^\n]{0,70}",
        text,
        flags=re.IGNORECASE,
    ):
        period_candidates.extend(_parsed_dates(phrase.group(0)))
    if not period_candidates:
        period_candidates = _parsed_dates(text[:12_000])
    period_end = max(period_candidates) if period_candidates else None
    return {
        "report_type": report_type,
        "reporting_period_end": period_end.isoformat() if period_end else None,
    }


def latest_required_period(report_type: str, today: date | None = None) -> date | None:
    today = today or datetime.now().date()
    if report_type == "annual":
        year = today.year if today >= date(today.year, 7, 29) else today.year - 1
        return date(year, 3, 31)
    if report_type != "interim":
        return None
    available_by = today - timedelta(days=45)
    candidates = [
        date(year, month, day)
        for year in range(today.year - 1, today.year + 1)
        for month, day in ((3, 31), (6, 30), (9, 30), (12, 31))
        if date(year, month, day) <= available_by
    ]
    return max(candidates) if candidates else None


def validate_report_freshness(metadata: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    report_type = metadata.get("report_type", "unknown")
    period_text = metadata.get("reporting_period_end")
    required = latest_required_period(report_type, today)
    try:
        period_end = date.fromisoformat(period_text) if period_text else None
    except ValueError:
        period_end = None
    is_latest = bool(period_end and required and period_end >= required)
    return {
        **metadata,
        "latest_required_period_end": required.isoformat() if required else None,
        "is_latest": is_latest,
    }
