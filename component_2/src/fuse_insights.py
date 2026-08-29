"""Create one plain-language explanation from verified upstream evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.llm_client import LLMClient
else:
    from .llm_client import LLMClient


SYSTEM_PROMPT = """
You produce a plain-language stock research overview for a non-expert investor.
Use only the supplied evidence. Treat missing or needs-review inputs as unavailable.
Never invent a price, event, cause, confidence, or report fact. Distinguish observed
association from causation. Do not expose implementation details or internal stage
names. Do not provide buy, sell, hold, or personalized financial advice. Return only
valid JSON matching the requested fields.
""".strip()

REQUIRED_STRING_FIELDS = (
    "headline",
    "plain_language_overview",
    "market_outlook",
    "company_report_takeaway",
    "external_context",
    "uncertainty",
    "non_advisory_note",
)
REQUIRED_LIST_FIELDS = ("potential", "key_risks", "what_could_change_the_picture", "evidence_used")


def _money(value: Any) -> str:
    try:
        return f"LKR {float(value):,.2f}"
    except (TypeError, ValueError):
        return "an unavailable price"


def _percent(value: Any) -> str:
    try:
        number = float(value)
        return f"{number:+.1f}%"
    except (TypeError, ValueError):
        return "an unavailable change"


def _sentence(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _market_outlook(market: dict[str, Any] | None) -> tuple[str, list[str], list[str]]:
    if not market:
        return "A verified market estimate was not available for this stock.", [], ["Market estimates were unavailable."]
    anomaly = market.get("anomaly") or {}
    actual = anomaly.get("actual_price_lkr", market.get("current_price_lkr"))
    expected = anomaly.get("expected_price_lkr")
    deviation = anomaly.get("signed_deviation_lkr")
    score = anomaly.get("liquidity_aware_score")
    threshold = anomaly.get("threshold")
    detected = bool(anomaly.get("detected"))
    deviation_text = (
        f"The latest price was {_money(actual)}, compared with an expected {_money(expected)} "
        f"for the same point, a difference of {_money(deviation)}. "
        if expected is not None else ""
    )
    if score is not None and threshold is not None:
        anomaly_text = (
            f"Its unusual-movement score was {float(score):.2f}, against a warning level of {float(threshold):.2f}. "
            f"This {'was' if detected else 'was not'} flagged as an unusual move."
        )
    else:
        anomaly_text = "The unusual-movement check was unavailable."
    horizons = [item for item in market.get("horizons", []) if item.get("estimated_close_lkr") is not None]
    paths = [
        f"{item.get('label')}: about {_money(item.get('estimated_close_lkr'))} ({_percent(item.get('change_from_latest_pct'))} from the latest price)"
        for item in horizons
    ]
    reliability = market.get("model_quality") or {}
    caution = ""
    risks: list[str] = []
    if reliability.get("advanced_model_beats_naive_mae") is False:
        caution = " These estimates need extra caution because a simple unchanged-price comparison performed better in testing."
        risks.append("The price estimates did not beat a simple unchanged-price comparison in testing.")
    unavailable = [item.get("label") for item in market.get("horizons", []) if item.get("status") == "not_validated"]
    if unavailable:
        risks.append(f"No validated estimate is available for {', '.join(unavailable)}.")
    path_text = "; ".join(paths)
    outlook = f"{deviation_text}{anomaly_text}"
    history = market.get("deviation_history") or {}
    if history.get("observations"):
        detected_count = int(history.get("detected_count") or 0)
        outlook += (
            f" Across {int(history['observations'])} recent trading sessions, "
            f"{detected_count} {'move was' if detected_count == 1 else 'moves were'} flagged as unusual."
        )
        largest = history.get("largest_recent_deviations") or []
        if largest:
            row = max(largest, key=lambda item: abs(float(item.get("deviation_pct") or 0)))
            direction = "above" if float(row.get("signed_deviation_lkr") or 0) >= 0 else "below"
            outlook += (
                f" The largest recent gap in this window was on {row.get('date')}, when the price was "
                f"{abs(float(row.get('deviation_pct') or 0)):.1f}% {direction} its expected level."
            )
    if path_text:
        outlook += f" The current paths are {path_text}."
    return outlook + caution, paths, risks


def _parse_date(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _nearby_event_context(market: dict[str, Any] | None, context: dict[str, Any] | None) -> str:
    """Describe timing overlap without converting it into a causal claim."""
    events = ((market or {}).get("deviation_history") or {}).get("detected_events") or []
    articles = [
        item for item in (context or {}).get("articles", [])
        if set(item.get("event_tags") or []) & {"geopolitical", "commodities", "macroeconomic"}
    ]
    closest: tuple[int, dict[str, Any], dict[str, Any]] | None = None
    for event in events:
        event_date = _parse_date(event.get("date"))
        if not event_date:
            continue
        for article in articles:
            article_date = _parse_date(article.get("published_at") or article.get("publishedAt"))
            if not article_date:
                continue
            days = abs((article_date.date() - event_date.date()).days)
            if days <= 10 and (closest is None or days < closest[0]):
                closest = (days, event, article)
    if not closest:
        return ""
    _, event, article = closest
    return (
        f" An unusual price gap on {event.get('date')} occurred near coverage titled "
        f"\"{article.get('title')}\". This timing makes the event relevant context, but it does not prove cause."
    )


def _report_takeaway(report: dict[str, Any] | None) -> tuple[str, list[str], list[str]]:
    if not report or report.get("status") != "completed":
        return "The uploaded report could not be used as confirmed evidence.", [], ["The company report still needs source review."]
    friendly = ((report.get("insight") or {}).get("investor_friendly_insight") or {})
    summary = _sentence(friendly.get("summary"), "The report was verified, but no short summary was available")
    strengths = [str(item) for item in friendly.get("key_strengths", []) if str(item).strip()]
    concerns = [str(item) for item in friendly.get("key_concerns", []) if str(item).strip()]
    return summary, strengths[:4], concerns[:4]


def _external_takeaway(context: dict[str, Any] | None) -> tuple[str, list[str], list[str], list[str]]:
    if not context:
        return "Current external context was unavailable.", [], [], []
    articles = context.get("articles") or []
    geopolitical = [item for item in articles if "geopolitical" in (item.get("event_tags") or [])]
    negative = [item for item in articles if (item.get("sentiment") or {}).get("label") == "negative"]
    selected = (geopolitical[:2] + [item for item in articles if item not in geopolitical])[:3]
    if selected:
        titles = "; ".join(str(item.get("title")) for item in selected)
        explanation = (
            f"Relevant recent coverage included: {titles}. These events may shape investor confidence, costs, or demand, "
            "but their timing alone does not prove that they caused this stock's price movement."
        )
    else:
        explanation = "No dated relevant news item was available in this analysis run."
    factors = ((context.get("external_factors") or {}).get("factors") or [])
    factor_notes = [
        f"{item.get('label')}: {_percent(item.get('change30dPct'))} over about 30 market days; {str(item.get('interpretation') or '').lower()}"
        for item in factors
    ]
    risks = [f"Negative coverage to monitor: {item.get('title')}" for item in negative[:2]]
    changes = [f"A meaningful change in {item.get('label')} could alter the wider market picture." for item in factors[:3]]
    return explanation, factor_notes, risks, changes


def build_local_fusion(evidence: dict[str, Any]) -> dict[str, Any]:
    """Create a complete plain-language result from verified upstream evidence."""
    selected = evidence.get("selected_stock") or {}
    company = selected.get("company_name") or selected.get("symbol") or "The selected company"
    market = evidence.get("market_evidence")
    report = evidence.get("report_evidence")
    context = evidence.get("external_context")
    market_text, paths, market_risks = _market_outlook(market)
    report_text, strengths, report_risks = _report_takeaway(report)
    external_text, factors, external_risks, changes = _external_takeaway(context)
    external_text += _nearby_event_context(market, context)
    anomaly = (market or {}).get("anomaly") or {}
    direction = "showed an unusual departure from its expected level" if anomaly.get("detected") else "remained within its expected movement range"
    headline = f"{company} {direction}, while company finances and current events add important context."
    overview = f"{market_text} {report_text} {external_text}"
    potential = []
    if paths:
        potential.append(f"The observed price pattern currently points to {paths[0].lower()}.")
    potential.extend(strengths[:2])
    if not potential:
        potential.append("No clear positive possibility could be confirmed from the available evidence.")
    key_risks = (report_risks + market_risks + external_risks)[:5]
    if not key_risks:
        key_risks.append("Unexpected company or market developments could move the price away from the estimated path.")
    change_items = changes[:4]
    change_items.append("A newer company report could materially change the financial picture.")
    uncertainty_parts = [
        "Price estimates are ranges, not promises.",
        "News and global-market relationships show context and timing, not proof of cause.",
    ]
    if (market or {}).get("model_quality", {}).get("advanced_model_beats_naive_mae") is False:
        uncertainty_parts.append("The advanced estimate did not outperform a simple unchanged-price comparison in testing.")
    report_period = (((report or {}).get("insight") or {}).get("metadata") or {}).get("reporting_period")
    if report_period:
        uncertainty_parts.append(f"The uploaded report covers the period ended {report_period}, so later company developments are not included in it.")
    return {
        "headline": headline,
        "plain_language_overview": overview,
        "market_outlook": market_text,
        "company_report_takeaway": report_text,
        "external_context": external_text + (f" Wider factors: {' '.join(factors)}" if factors else ""),
        "potential": potential[:3],
        "key_risks": key_risks,
        "what_could_change_the_picture": change_items[:5],
        "uncertainty": " ".join(uncertainty_parts),
        "evidence_used": [
            "Historical prices, trading volume, expected price, deviation, and unusual-movement score",
            "Page-verified figures from the uploaded company report",
            "Dated company and market news plus observed gold, oil, and currency relationships",
        ],
        "non_advisory_note": "This is an informational research summary, not buying or selling advice.",
    }


def build_prompt(evidence: dict[str, Any]) -> str:
    return f"""
Create a concise unified insight from the evidence JSON below.

Required JSON object:
{{
  "headline": "one factual sentence",
  "plain_language_overview": "2-4 short sentences explaining the complete picture",
  "market_outlook": "plain explanation of the available forecast horizons, anomaly, and reliability warning",
  "company_report_takeaway": "plain report summary, or clearly say it needs review",
  "external_context": "relevant company/market events and factor associations without causal overclaiming",
  "potential": ["up to three evidence-based possibilities, not advice"],
  "key_risks": ["up to five evidence-based risks"],
  "what_could_change_the_picture": ["up to five events or conditions"],
  "uncertainty": "what is unknown, missing, weak, stale, or not validated",
  "evidence_used": ["short descriptions of the evidence actually used"],
  "non_advisory_note": "This is an informational research summary, not buying or selling advice."
}}

Rules:
- Never turn a six-month unavailable status into a forecast.
- If the advanced market model did not beat its baseline, say the estimates should be treated cautiously.
- Use report facts only when their evidence passed page-quote verification.
- Mention only news supplied in the evidence and avoid saying an event caused a price move.
- Do not assign an overall confidence percentage.

Evidence JSON:
{json.dumps(evidence, ensure_ascii=False)}
""".strip()


def validate_output(value: Any) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    if not isinstance(value, dict):
        return None, ["The unified explanation was not returned as an object."]

    cleaned: dict[str, Any] = {}
    for field in REQUIRED_STRING_FIELDS:
        item = value.get(field)
        if not isinstance(item, str) or not item.strip():
            warnings.append(f"The unified explanation is missing {field}.")
            cleaned[field] = ""
        else:
            cleaned[field] = item.strip()

    for field in REQUIRED_LIST_FIELDS:
        items = value.get(field)
        if not isinstance(items, list):
            warnings.append(f"The unified explanation is missing {field}.")
            cleaned[field] = []
        else:
            cleaned[field] = [str(item).strip() for item in items if str(item).strip()][:5]

    cleaned["non_advisory_note"] = (
        "This is an informational research summary, not buying or selling advice."
    )
    return cleaned, warnings


def fuse(evidence: dict[str, Any]) -> dict[str, Any]:
    local_insight = build_local_fusion(evidence)
    if os.getenv("USE_AZURE_OPENAI", "false").strip().lower() not in {"1", "true", "yes"}:
        return {"status": "completed", "insight": local_insight, "warnings": []}

    response = LLMClient().run_json_prompt(build_prompt(evidence), instructions=SYSTEM_PROMPT)
    if response.get("error"):
        return {
            "status": "completed",
            "insight": local_insight,
            "warnings": [],
            "fallback_used": True,
        }
    insight, warnings = validate_output(response.get("parsed_output"))
    if not insight or warnings:
        return {
            "status": "completed",
            "insight": local_insight,
            "warnings": [],
            "fallback_used": True,
        }
    return {
        "status": "completed",
        "insight": insight,
        "warnings": [],
        "runtime_seconds": response.get("runtime_seconds"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fuse one analysis evidence payload.")
    parser.add_argument("--input", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        evidence = json.loads(args.input.read_text(encoding="utf-8"))
        result = fuse(evidence)
    except Exception as error:  # noqa: BLE001
        result = {"status": "failed", "insight": None, "warnings": [str(error)]}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
