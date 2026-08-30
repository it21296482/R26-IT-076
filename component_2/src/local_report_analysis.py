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
    MetricSpec("operating_profit", "Results from operating activities", (r"(?m)^\s*Results from operating activities\s*$",), 0),
    MetricSpec("finance_cost", "Finance cost", (r"(?m)^\s*Finance cost\s*$",), 0),
    MetricSpec(
        "profit_after_tax",
        "Group profit or loss after tax",
        (
            r"(?m)^\s*Profit\s*/\s*\(Loss\)\s*after tax for the period\s*$",
            r"(?m)^\s*Profit\s*/?\s*\(loss\)\s*for the period\s+from continuing operations\s*$",
            r"(?m)^\s*Profit\s*/?\s*\(loss\)\s*for the period\s*$",
            r"(?m)^\s*Profit for the period\s*$",
        ),
        0,
    ),
    MetricSpec(
        "earnings_per_share",
        "Earnings or loss per share",
        (r"(?m)^\s*Basic\s*/?\s*diluted earnings per share\s*\(Rs\.\)\s*$",),
        0,
    ),
    MetricSpec("total_assets", "Total assets", (r"(?m)^\s*Total Assets\s*$",), 0),
    MetricSpec("total_equity", "Total equity", (r"(?m)^\s*Total Equity\s*$",), 0),
    MetricSpec("net_assets_per_share", "Net assets per ordinary share", (r"(?m)^\s*Net Assets per ordinary Share\s*\(Rs\.\)\s*$",), 0),
    MetricSpec("last_traded_price", "Last traded market price", (r"(?m)^\s*Last traded price recorded for 3 months ended\s*$",), 0),
    MetricSpec(
        "operating_cash_flow",
        "Net cash from operating activities",
        (r"(?m)^\s*Net cash generated from\s*/?\s*\(used in\)\s*operating activities\s*$",),
        0,
    ),
    MetricSpec(
        "cash_generated_from_operations",
        "Cash generated from operations before interest and tax payments",
        (r"(?m)^\s*Cash generated from\s*/?\s*\(used in\)\s*operations\s*$",),
        0,
    ),
    MetricSpec(
        "capital_expenditure",
        "Acquisition and construction of property, plant and equipment",
        (r"(?m)^\s*Acquisition and construction of property, plant and equipment\s*$",),
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
    cumulative_fields = {
        "revenue", "gross_profit", "operating_profit", "finance_cost", "profit_after_tax", "earnings_per_share",
    }
    return 2 if spec.key in cumulative_fields and len(numbers) >= 4 else spec.value_index


def _statement_values(numbers: list[tuple[float, str]], spec: MetricSpec) -> list[tuple[float, str]]:
    if spec.key in {"earnings_per_share", "net_assets_per_share", "last_traded_price"}:
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


def _comparison_text(current: float, previous: float) -> str:
    return f"{abs(_percent_change(current, previous) or 0):.0f}%"


def _find_page_row(page: dict[str, Any], pattern: str) -> dict[str, Any] | None:
    text = str(page.get("text") or "")
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    numbers = _numbers_after_match(text, match, limit=5_000)
    if len(numbers) < 2:
        return None
    quote_end = min(len(text), match.end() + 4_500)
    return {
        "values": [item[0] for item in numbers],
        "page_number": int(page["page_number"]),
        "source_quote": text[match.start():quote_end].strip(),
    }


def _segment_strengths(pages: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    strengths: list[str] = []
    evidence: list[dict[str, Any]] = []
    for page in pages:
        text = str(page.get("text") or "")
        if "Segment Information - Group" not in text or "Leisure" not in text or "Plantation" not in text:
            continue
        revenue = _find_page_row(page, r"^\s*Revenue\s*/?\s*income\s*$")
        gross_profit = _find_page_row(page, r"^\s*Gross profit\s*$")
        operating = _find_page_row(page, r"^\s*Results from Operating\s+Activities\s*$")
        after_tax = _find_page_row(page, r"^\s*Profit after taxation from\s+continuing operations\s*$")
        for field, row in (
            ("segment_revenue", revenue),
            ("segment_gross_profit", gross_profit),
            ("segment_operating_result", operating),
            ("segment_after_tax_result", after_tax),
        ):
            if row and len(row["values"]) >= 14:
                evidence.append({
                    "field": field,
                    "value": row["values"],
                    "page_number": row["page_number"],
                    "source_quote": row["source_quote"],
                })
        if operating and len(operating["values"]) >= 14:
            values = operating["values"]
            if values[2] > 0 > values[3]:
                strengths.append(
                    f"Leisure and Travel moved from an operating loss of {_format_lkr_thousands(abs(values[3]))} "
                    f"to an operating profit of {_format_lkr_thousands(values[2])}."
                )
            if values[4] > 0 > values[5]:
                strengths.append(
                    f"Construction, Manufacturing and Trading moved from an operating loss of "
                    f"{_format_lkr_thousands(abs(values[5]))} to an operating profit of {_format_lkr_thousands(values[4])}."
                )
        if after_tax and len(after_tax["values"]) >= 14:
            values = after_tax["values"]
            if values[4] > 0 > values[5]:
                strengths.append(
                    f"Construction, Manufacturing and Trading also moved from an after-tax loss of "
                    f"{_format_lkr_thousands(abs(values[5]))} to a profit of {_format_lkr_thousands(values[4])}."
                )
        if revenue and gross_profit and len(revenue["values"]) >= 14 and len(gross_profit["values"]) >= 14:
            revenue_values = revenue["values"]
            gross_values = gross_profit["values"]
            if revenue_values[6] > revenue_values[7] and gross_values[6] > gross_values[7]:
                strengths.append(
                    f"Plantation revenue increased {_comparison_text(revenue_values[6], revenue_values[7])} to "
                    f"{_format_lkr_thousands(revenue_values[6])}, while plantation gross profit rose from "
                    f"{_format_lkr_thousands(gross_values[7])} to {_format_lkr_thousands(gross_values[6])}."
                )
        break
    return strengths, evidence


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

    def value(key: str) -> float | None:
        return metric_map.get(key, {}).get("value")

    prior_map = {
        key: _prior_value(pages, spec)
        for key, spec in spec_map.items()
        if key in metric_map
    }

    revenue = value("revenue")
    gross_profit = value("gross_profit")
    operating_profit = value("operating_profit")
    profit = value("profit_after_tax")
    eps = value("earnings_per_share")
    finance_cost = value("finance_cost")
    operating_cash = value("operating_cash_flow")
    cash_generated = value("cash_generated_from_operations")
    capex = value("capital_expenditure")
    assets = value("total_assets")
    equity = value("total_equity")
    nav_per_share = value("net_assets_per_share")
    market_price = value("last_traded_price")
    previous_revenue = prior_map.get("revenue")
    previous_finance_cost = prior_map.get("finance_cost")
    previous_equity = prior_map.get("total_equity")
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
    previous_gross_profit = prior_map.get("gross_profit")
    gross_profit_change = _percent_change(gross_profit, previous_gross_profit)
    if gross_profit_change is not None and gross_profit_change > 0:
        point = f"Gross profit increased by about {gross_profit_change:.0f}%"
        if revenue and previous_revenue and gross_profit is not None and previous_gross_profit is not None:
            current_margin = gross_profit / revenue * 100
            previous_margin = previous_gross_profit / previous_revenue * 100
            margin_word = "improved" if current_margin > previous_margin else "moved"
            point += f", while gross margin {margin_word} from about {previous_margin:.1f}% to {current_margin:.1f}%"
        strengths.append(f"{point}.")
    previous_operating_profit = prior_map.get("operating_profit")
    operating_profit_change = _percent_change(operating_profit, previous_operating_profit)
    if operating_profit_change is not None and operating_profit_change > 0:
        strengths.append(
            f"Operating profit increased by about {operating_profit_change:.0f}% to "
            f"{_format_lkr_thousands(operating_profit)}."
        )
    previous_profit = prior_map.get("profit_after_tax")
    if profit is not None and previous_profit is not None and profit < 0 and previous_profit < 0 and abs(profit) < abs(previous_profit):
        improvement = (1 - abs(profit) / abs(previous_profit)) * 100
        strengths.append(
            f"The group loss after tax narrowed by about {improvement:.0f}%, from "
            f"{_format_lkr_thousands(abs(previous_profit))} to {_format_lkr_thousands(abs(profit))}."
        )
    previous_eps = prior_map.get("earnings_per_share")
    if eps is not None and previous_eps is not None and eps < 0 and previous_eps < 0 and abs(eps) < abs(previous_eps):
        strengths.append(f"Loss per share improved from LKR {abs(previous_eps):.2f} to LKR {abs(eps):.2f}.")
    segment_strengths, segment_evidence = _segment_strengths(pages)
    strengths.extend(segment_strengths)
    previous_cash_generated = prior_map.get("cash_generated_from_operations")
    if cash_generated is not None and previous_cash_generated is not None and cash_generated > 0 > previous_cash_generated:
        strengths.append(
            f"Cash generated from operations before interest and tax payments turned positive at "
            f"{_format_lkr_thousands(cash_generated)}, compared with an outflow of "
            f"{_format_lkr_thousands(abs(previous_cash_generated))} previously."
        )
    previous_operating_cash = prior_map.get("operating_cash_flow")
    if operating_cash is not None and previous_operating_cash is not None and operating_cash > previous_operating_cash:
        if operating_cash < 0:
            strengths.append(
                f"Net operating cash outflow improved substantially to {_format_lkr_thousands(abs(operating_cash))}, "
                f"from {_format_lkr_thousands(abs(previous_operating_cash))} in the comparison period."
            )
        else:
            strengths.append(
                f"Net cash from operating activities improved to {_format_lkr_thousands(operating_cash)}."
            )
    previous_capex = prior_map.get("capital_expenditure")
    if capex is not None and previous_capex is not None and abs(capex) > abs(previous_capex):
        strengths.append(
            f"Investment in property, plant and equipment increased from {_format_lkr_thousands(abs(previous_capex))} "
            f"to {_format_lkr_thousands(abs(capex))}; this shows expansion spending, although returns still need to be proven."
        )
    previous_assets = prior_map.get("total_assets")
    asset_change = _percent_change(assets, previous_assets)
    if asset_change is not None and asset_change > 0:
        point = f"Total assets increased by about {asset_change:.1f}% to {_format_lkr_thousands(assets)}"
        if equity_change is not None and equity_change > 0:
            point += f", while total equity increased by about {equity_change:.1f}% to {_format_lkr_thousands(equity)}"
        strengths.append(f"{point}.")
    previous_nav = prior_map.get("net_assets_per_share")
    if nav_per_share is not None and previous_nav is not None and nav_per_share > previous_nav:
        strengths.append(f"Net asset value per share increased from LKR {previous_nav:.2f} to LKR {nav_per_share:.2f}.")
    if market_price is not None and nav_per_share and nav_per_share > 0:
        nav_percentage = market_price / nav_per_share * 100
        strengths.append(
            f"At the report date, the LKR {market_price:.2f} market price was about {nav_percentage:.0f}% of the reported "
            f"LKR {nav_per_share:.2f} net asset value per share. This gap is notable, but does not by itself prove undervaluation."
        )
    if operating_cash is not None and operating_cash > 0:
        strengths.append(f"Operations generated {_format_lkr_thousands(operating_cash)} in cash.")
    if profit is not None and profit < 0:
        concerns.append(f"The group recorded a loss of {_format_lkr_thousands(abs(profit))}.")
    if finance_cost is not None:
        change_text = f", about {finance_cost_change:.0f}% above the comparison period" if finance_cost_change is not None and finance_cost_change > 0 else ""
        concerns.append(f"Finance costs were {_format_lkr_thousands(abs(finance_cost))}{change_text}.")
    if operating_cash is not None and operating_cash < 0:
        concerns.append(f"Net operating cash flow remained an outflow of {_format_lkr_thousands(abs(operating_cash))}.")
    if finance_cost is not None and operating_profit is not None and abs(finance_cost) > max(operating_profit, 0):
        concerns.append("Finance costs remained higher than operating profit, so financing pressure still outweighs the operating recovery.")
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
    source_evidence.extend(segment_evidence)
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
