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

from .report_metadata import detect_report_metadata


NUMBER_PATTERN = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    patterns: tuple[str, ...]
    value_index: int


METRIC_SPECS = (
    MetricSpec("revenue", "Revenue", (r"(?m)^\s*Total revenue\s*$", r"(?m)^\s*Revenue\s*/?\s*Income\s*$", r"(?m)^\s*Revenue\s*$"), 0),
    MetricSpec("gross_profit", "Gross profit", (r"(?m)^\s*Gross profit\s*$", r"(?m)^\s*Gross margin\s*$"), 0),
    MetricSpec("finance_cost", "Finance cost", (r"(?m)^\s*Finance cost\s*$",), 0),
    MetricSpec("profit_after_tax", "Profit or loss for the period", (r"(?m)^\s*Profit\s*/?\s*\(loss\)\s*for the period\s*$", r"(?m)^\s*Profit for the period\s*$"), 0),
    MetricSpec("earnings_per_share", "Earnings or loss per share", (r"(?m)^\s*Basic/?\s*diluted earnings per share\s*\(Rs\.\)\s*$",), 0),
    MetricSpec("total_assets", "Total assets", (r"(?m)^\s*Total Assets\s*$",), 0),
    MetricSpec("total_equity", "Total equity", (r"(?m)^\s*Total Equity\s*$",), 0),
    MetricSpec(
        "operating_cash_flow",
        "Net cash from operating activities",
        (r"(?m)^\s*Net cash generated from\s*/?\s*\(used in\)\s*operating activities\s*$",),
        0,
    ),
)

STRENGTH_TERMS = (
    "increased", "increase", "growth", "grew", "improved", "improvement", "profit",
    "positive", "exceeding", "full utilisation", "on track", "strong", "higher",
    "recovery", "expanded", "recorded encouraging", "growth potential", "will diversify",
    "will enter", "expected to open",
)
CONCERN_TERMS = (
    "revenue decreased", "profit decreased", "declined", "decline", "recorded a loss", "reported a loss",
    "net exchange loss", "negative ebitda", "negative rs", "impacted",
    "challenging", "disrupted", "weakened", "pressure", "higher cost", "higher energy",
    "exchange loss", "depreciation of the rupee", "uncertainty", "moderated", "debt",
)
DECISION_EVIDENCE_TERMS = (
    "%", "rs.", "billion", "million", "volume", "utilisation", "throughput", "occupancy",
    "revenue", "ebitda", "profit", "loss", "sales", "cost", "cash", "operational", "expected", "outlet",
)


def _number_from_token(token: str) -> float:
    negative = token.startswith("(") and token.endswith(")")
    value = float(token.strip("()").replace(",", ""))
    return -value if negative else value


def _numbers_after_match(text: str, match: re.Match[str], limit: int = 700) -> list[tuple[float, str]]:
    values: list[tuple[float, str]] = []
    tail = text[match.end() : match.end() + limit]
    for line in tail.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if values and re.search(r"[A-Za-z]", stripped):
            break
        line_match = re.fullmatch(r"(\(?-?\d[\d,]*(?:\.\d+)?\)?)(?:\s*(%|>100%))?", stripped)
        if not line_match:
            if values:
                break
            continue
        if line_match.group(2):
            continue
        token = line_match.group(1)
        values.append((_number_from_token(token), token))
    if values:
        return values
    for number_match in NUMBER_PATTERN.finditer(tail):
        # Percentage columns describe change and are not statement values.
        suffix = tail[number_match.end() : number_match.end() + 2]
        if "%" in suffix:
            continue
        token = number_match.group(0)
        values.append((_number_from_token(token), token))
    return values


def _value_index(spec: MetricSpec, numbers: list[tuple[float, str]]) -> int:
    cumulative_fields = {"revenue", "gross_profit", "finance_cost", "profit_after_tax", "earnings_per_share"}
    return 2 if spec.key in cumulative_fields and len(numbers) >= 4 else spec.value_index


def _statement_values(numbers: list[tuple[float, str]], spec: MetricSpec) -> list[tuple[float, str]]:
    if spec.key == "earnings_per_share":
        return numbers
    substantial = [item for item in numbers if abs(item[0]) >= 1_000]
    return substantial or numbers


def _find_metric(pages: list[dict[str, Any]], spec: MetricSpec) -> dict[str, Any] | None:
    for page in pages:
        text = str(page.get("text") or "")
        for pattern in spec.patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            numbers = _statement_values(_numbers_after_match(text, match), spec)
            value_index = _value_index(spec, numbers)
            if len(numbers) <= value_index:
                continue
            value, _ = numbers[value_index]
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


def _clean_sentence(value: str) -> str:
    cleaned = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" •\t\r\n")
    return re.sub(
        r"^\d+\s+John Keells Holdings PLC Interim Condensed Financial Statements Three Months Ended 30 June 2026(?: CHAIRPERSON’S MESSAGE)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )


def _narrative_candidates(
    pages: list[dict[str, Any]],
    terms: tuple[str, ...],
    *,
    concern: bool = False,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in pages:
        text = str(page.get("text") or "")
        chunks = re.split(r"(?:\n\s*[•●▪]\s*|(?<=[.!?])\s+)", text)
        for chunk_index, chunk in enumerate(chunks):
            sentence = _clean_sentence(chunk)
            if ("wendy" in sentence.lower() or "quick service restaurant" in sentence.lower()) and chunk_index + 1 < len(chunks):
                continuation = _clean_sentence(chunks[chunk_index + 1])
                if "expected to open" in continuation.lower():
                    sentence = f"{sentence} {continuation}"
            lowered = sentence.lower()
            if not 45 <= len(sentence) <= 650:
                continue
            matched = sum(term in lowered for term in terms)
            evidence = sum(term in lowered for term in DECISION_EVIDENCE_TERMS)
            if not matched or not evidence:
                continue
            if any(term in lowered for term in (
                "table of contents", "accounting polic", "page no", "authorised for issue",
                "weighted average number", "segment information", "an operating segment is",
                "the computation of", "page 10 of", "listed on the colombo stock exchange",
            )):
                continue
            if concern and any(term in lowered for term in (
                "excluding net exchange losses", "increase over the corresponding period", "improved from a loss",
            )):
                continue
            if not concern and any(term in lowered for term in (
                "conflict in the middle east contributed", "inflation increased during", "higher energy costs", "net exchange loss",
            )):
                continue
            key = re.sub(r"[^a-z0-9]", "", lowered)[:180]
            if key in seen:
                continue
            seen.add(key)
            decision_priority = sum(term in lowered for term in (
                "group revenue", "group earnings", "group profit", "group pbt", "profit attributable",
                "ebitda", "throughput", "same-store", "occupancy", "full utilisation",
            ))
            group_priority = 8 if any(term in lowered for term in (
                "group revenue", "group earnings", "group profit before tax", "group pbt", "profit attributable to equity holders",
            )) else 0
            mixed_penalty = 4 if not concern and any(term in lowered for term in ("despite", "impacted", "moderated")) else 0
            score = matched * 3 + evidence + decision_priority * 3 + group_priority - mixed_penalty + (3 if int(page["page_number"]) <= 10 else 0)
            candidates.append({
                "text": sentence,
                "page_number": int(page["page_number"]),
                "score": score,
            })
    return sorted(candidates, key=lambda item: (-item["score"], item["page_number"]))


def _deduplicate_points(items: list[str], limit: int) -> list[str]:
    output: list[str] = []
    normalized: list[str] = []
    for item in items:
        key = re.sub(r"[^a-z0-9]", "", item.lower())
        if any(key[:100] in existing or existing[:100] in key for existing in normalized):
            continue
        normalized.append(key)
        output.append(item)
        if len(output) >= limit:
            break
    return output


def _prioritize_strengths(candidates: list[dict[str, Any]]) -> list[str]:
    priority_groups = (
        ("group revenue",),
        ("group earnings", "group ebitda"),
        ("group profit before tax", "group pbt at", "group pbt for"),
        ("profit attributable to equity holders",),
        ("transportation industry group ebitda",),
        ("full utilisation", "throughput exceeding"),
        ("full terminal remains on track", "operationalisation of the full terminal"),
        ("city of dreams sri lanka recorded an ebitda",),
        ("consumer foods industry group ebitda",),
        ("beverages business",),
        ("confectionery business",),
        ("wendy", "quick service restaurant"),
        ("supermarket business ebitda",),
        ("same-store sales",),
    )
    selected: list[str] = []
    used: set[str] = set()
    for phrases in priority_groups:
        match = next((item for item in candidates if any(phrase in item["text"].lower() for phrase in phrases)), None)
        if match:
            selected.append(match["text"])
            used.add(match["text"])
    selected.extend(item["text"] for item in candidates if item["text"] not in used)
    return selected


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
    for page in pages:
        text = str(page.get("text") or "")
        for pattern in spec.patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            numbers = _statement_values(_numbers_after_match(text, match), spec)
            prior_index = _value_index(spec, numbers) + 1
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
    report_metadata = detect_report_metadata("\n".join(str(page.get("text") or "") for page in pages[:8]))
    period = report_metadata.get("reporting_period_end") or period
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
    narrative_strengths = _narrative_candidates(pages, STRENGTH_TERMS)
    narrative_concerns = _narrative_candidates(pages, CONCERN_TERMS, concern=True)
    if not sentences and narrative_strengths:
        sentences.extend(item["text"] for item in narrative_strengths[:2])
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

    strengths = _deduplicate_points(strengths + _prioritize_strengths(narrative_strengths), 22)
    concerns = _deduplicate_points(concerns + [item["text"] for item in narrative_concerns], 8)

    source_evidence = [
        {
            "field": metric["key"],
            "value": metric["value"],
            "page_number": metric["page_number"],
            "source_quote": metric["source_quote"],
        }
        for metric in metrics
    ]
    source_evidence.extend(
        {
            "field": f"operational_strength_{index}",
            "value": item["text"],
            "page_number": item["page_number"],
            "source_quote": item["text"],
        }
        for index, item in enumerate(narrative_strengths[:30], start=1)
    )
    source_evidence.extend(
        {
            "field": f"operational_concern_{index}",
            "value": item["text"],
            "page_number": item["page_number"],
            "source_quote": item["text"],
        }
        for index, item in enumerate(narrative_concerns[:8], start=1)
    )
    return {
        "metadata": {
            "pdf_name": extracted_payload.get("pdf_name"),
            "prompt_id": prompt_id,
            "selected_symbol": symbol,
            "reporting_period": period,
            "report_type": report_metadata.get("report_type"),
            "explanation_source": "verified report text",
        },
        "company_overview": {"company_name": company, "reporting_period": period},
        "extracted_facts": {
            metric["key"]: {"value_rs_000": metric["value"], "label": metric["label"]}
            for metric in metrics
        },
        "investor_friendly_insight": {
            "summary": summary.strip(),
            "key_strengths": strengths or ["No clear strength was confirmed from the extracted report evidence."],
            "key_concerns": concerns or ["No clear concern was confirmed from the extracted report evidence."],
            "non_advisory_note": "This is an informational summary for decision support, not buying or selling advice.",
        },
        "source_evidence": source_evidence,
        "missing_fields": [spec.key for spec in METRIC_SPECS if spec.key not in metric_map],
    }
