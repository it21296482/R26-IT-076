"""Build a conservative report summary directly from verified PDF text.

The external explanation service can improve phrasing, but it must not be a
single point of failure. This module extracts common financial statement rows,
keeps the exact page text used for every figure, and produces a short summary
without guessing missing values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


NUMBER_PATTERN = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    patterns: tuple[str, ...]
    value_index: int


METRIC_SPECS = (
    MetricSpec("revenue", "Revenue", (r"Revenue\s*/?\s*Income", r"Revenue"), 2),
    MetricSpec("gross_profit", "Gross profit", (r"Gross profit", r"Gross margin"), 2),
    MetricSpec("finance_cost", "Finance cost", (r"Finance cost",), 2),
    MetricSpec("profit_after_tax", "Profit or loss for the period", (r"Profit\s*/?\s*\(loss\)\s*for the period",), 2),
    MetricSpec("earnings_per_share", "Earnings or loss per share", (r"Earnings\s*/?\s*\(loss\)\s*per Share\s*-?\s*Rs\.",), 2),
    MetricSpec("total_assets", "Total assets", (r"Total Assets",), 0),
    MetricSpec("total_equity", "Total equity", (r"Total Equity",), 0),
    MetricSpec(
        "operating_cash_flow",
        "Net cash from operating activities",
        (r"Net cash generated from\s*/?\s*\(used in\)\s*operating activities",),
        0,
    ),
)


def _number_from_token(token: str) -> float:
    negative = token.startswith("(") and token.endswith(")")
    value = float(token.strip("()").replace(",", ""))
    return -value if negative else value


def _numbers_after_match(text: str, match: re.Match[str], limit: int = 700) -> list[tuple[float, str]]:
    values: list[tuple[float, str]] = []
    tail = text[match.end() : match.end() + limit]
    for number_match in NUMBER_PATTERN.finditer(tail):
        # Percentage columns describe change and are not statement values.
        suffix = tail[number_match.end() : number_match.end() + 2]
        if "%" in suffix:
            continue
        token = number_match.group(0)
        values.append((_number_from_token(token), token))
    return values


def _find_metric(pages: list[dict[str, Any]], spec: MetricSpec) -> dict[str, Any] | None:
    for page in pages:
        text = str(page.get("text") or "")
        for pattern in spec.patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            numbers = _numbers_after_match(text, match)
            if len(numbers) <= spec.value_index:
                continue
            value, _ = numbers[spec.value_index]
            quote = text[match.start() : min(len(text), match.end() + 520)].strip()
            return {
                "key": spec.key,
                "label": spec.label,
                "value": value,
                "page_number": int(page["page_number"]),
                "source_quote": quote,
            }
    return None


def _find_company_and_period(pages: list[dict[str, Any]], company_name: str) -> tuple[str, str | None]:
    first_pages = "\n".join(str(page.get("text") or "") for page in pages[:3])
    company = company_name
    company_match = re.search(r"([A-Z][A-Za-z&.,' -]+?\s(?:PLC|Limited|Ltd))\b", first_pages)
    if company_match:
        company = re.sub(r"\s+", " ", company_match.group(1)).strip()
    period_match = re.search(
        r"(?:period|year|quarter)\s+ended\s+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})",
        first_pages,
        flags=re.IGNORECASE,
    )
    return company, period_match.group(1) if period_match else None


def _format_lkr_thousands(value: float | None) -> str:
    if value is None:
        return "an unavailable amount"
    absolute_rupees = abs(value) * 1_000
    sign = "negative " if value < 0 else ""
    if absolute_rupees >= 1_000_000_000:
        return f"{sign}LKR {absolute_rupees / 1_000_000_000:.2f} billion"
    return f"{sign}LKR {absolute_rupees / 1_000_000:.2f} million"


def _percent_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in {None, 0}:
        return None
    return ((current / previous) - 1) * 100


def _prior_value(pages: list[dict[str, Any]], spec: MetricSpec) -> float | None:
    prior_index = spec.value_index + 1
    for page in pages:
        text = str(page.get("text") or "")
        for pattern in spec.patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            numbers = _numbers_after_match(text, match)
            if len(numbers) > prior_index:
                return numbers[prior_index][0]
    return None


def build_local_report_insight(
    extracted_payload: dict[str, Any],
    company_name: str,
    symbol: str,
    prompt_id: str,
) -> dict[str, Any]:
    """Return a grounded insight using only statement rows found in the PDF."""
    pages = extracted_payload.get("pages", [])
    company, period = _find_company_and_period(pages, company_name)
    metrics = [metric for spec in METRIC_SPECS if (metric := _find_metric(pages, spec))]
    metric_map = {metric["key"]: metric for metric in metrics}
    spec_map = {spec.key: spec for spec in METRIC_SPECS}

    revenue = metric_map.get("revenue", {}).get("value")
    profit = metric_map.get("profit_after_tax", {}).get("value")
    finance_cost = metric_map.get("finance_cost", {}).get("value")
    operating_cash = metric_map.get("operating_cash_flow", {}).get("value")
    equity = metric_map.get("total_equity", {}).get("value")
    previous_revenue = _prior_value(pages, spec_map["revenue"])
    previous_finance_cost = _prior_value(pages, spec_map["finance_cost"])
    previous_equity = _prior_value(pages, spec_map["total_equity"])
    revenue_change = _percent_change(revenue, previous_revenue)
    finance_cost_change = _percent_change(abs(finance_cost) if finance_cost is not None else None, abs(previous_finance_cost) if previous_finance_cost is not None else None)
    equity_change = _percent_change(equity, previous_equity)

    period_text = f" for the period ended {period}" if period else " in the uploaded reporting period"
    sentences: list[str] = []
    if revenue is not None:
        change_text = f", about {abs(revenue_change):.0f}% {'higher' if revenue_change >= 0 else 'lower'} than the comparison period" if revenue_change is not None else ""
        sentences.append(f"Revenue was {_format_lkr_thousands(revenue)}{change_text}.")
    if profit is not None:
        result_word = "a loss" if profit < 0 else "a profit"
        sentences.append(f"The group reported {result_word} of {_format_lkr_thousands(abs(profit))}.")
    if operating_cash is not None:
        cash_word = "generated" if operating_cash >= 0 else "used"
        sentences.append(f"Operating activities {cash_word} {_format_lkr_thousands(abs(operating_cash))} in cash.")
    summary = f"{company}{period_text}. " + " ".join(sentences)

    strengths: list[str] = []
    concerns: list[str] = []
    if revenue_change is not None and revenue_change > 0:
        strengths.append(f"Revenue increased by about {revenue_change:.0f}% from the comparison period.")
    if operating_cash is not None and operating_cash > 0:
        strengths.append(f"Operations generated {_format_lkr_thousands(operating_cash)} in cash.")
    if profit is not None and profit < 0:
        concerns.append(f"The group recorded a loss of {_format_lkr_thousands(abs(profit))}.")
    if finance_cost is not None:
        change_text = f", about {finance_cost_change:.0f}% above the comparison period" if finance_cost_change is not None and finance_cost_change > 0 else ""
        concerns.append(f"Finance costs were {_format_lkr_thousands(abs(finance_cost))}{change_text}.")
    if equity_change is not None and equity_change < 0:
        concerns.append(f"Total equity decreased by about {abs(equity_change):.0f}% from the comparison date.")

    source_evidence = [
        {
            "field": metric["key"],
            "value": metric["value"],
            "page_number": metric["page_number"],
            "source_quote": metric["source_quote"],
        }
        for metric in metrics
    ]
    return {
        "metadata": {
            "pdf_name": extracted_payload.get("pdf_name"),
            "prompt_id": prompt_id,
            "selected_symbol": symbol,
            "reporting_period": period,
            "explanation_source": "verified report text",
        },
        "company_overview": {"company_name": company, "reporting_period": period},
        "extracted_facts": {
            metric["key"]: {"value_rs_000": metric["value"], "label": metric["label"]}
            for metric in metrics
        },
        "investor_friendly_insight": {
            "summary": summary.strip(),
            "key_strengths": strengths[:4] or ["No clear strength was confirmed from the extracted statement rows."],
            "key_concerns": concerns[:4] or ["No clear concern was confirmed from the extracted statement rows."],
            "non_advisory_note": "This is an informational summary for decision support, not buying or selling advice.",
        },
        "source_evidence": source_evidence,
        "missing_fields": [spec.key for spec in METRIC_SPECS if spec.key not in metric_map],
    }
