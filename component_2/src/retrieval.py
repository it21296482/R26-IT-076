"""Find relevant annual-report pages for investor-related fields.

The retrieval layer keeps prompts focused by selecting the strongest pages for
revenue, risks, governance, outlook, ratios, and other investor categories.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .schemas import INVESTOR_FIELD_GROUPS
from .utils import normalize_whitespace


def flatten_field_metadata() -> dict[str, dict[str, Any]]:
    """Flatten nested category definitions into field-level metadata."""
    metadata: dict[str, dict[str, Any]] = {}
    for category, fields in INVESTOR_FIELD_GROUPS.items():
        for field, info in fields.items():
            metadata[field] = {"category": category, **info}
    return metadata


FIELD_METADATA = flatten_field_metadata()


def page_texts(extracted_payload: dict[str, Any]) -> list[str]:
    """Return normalized page text strings from an extracted PDF payload."""
    return [page.get("text", "") for page in extracted_payload.get("pages", [])]


def keyword_score(text: str, aliases: list[str]) -> float:
    """Score how often field aliases appear in one page."""
    lowered = text.lower()
    score = 0.0
    for alias in aliases:
        score += lowered.count(alias.lower()) * 2.0
    return score


def token_cosine_score(text: str, query: str) -> float:
    """Compute a lightweight token-overlap similarity score."""
    query_tokens = re.findall(r"[a-z0-9]+", query.lower())
    text_tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not query_tokens or not text_tokens:
        return 0.0
    query_counts = defaultdict(int)
    text_counts = defaultdict(int)
    for token in query_tokens:
        query_counts[token] += 1
    for token in text_tokens:
        text_counts[token] += 1
    dot = sum(query_counts[token] * text_counts.get(token, 0) for token in query_counts)
    mag_a = math.sqrt(sum(value * value for value in query_counts.values()))
    mag_b = math.sqrt(sum(value * value for value in text_counts.values()))
    if not mag_a or not mag_b:
        return 0.0
    return dot / (mag_a * mag_b)


def rank_pages_for_field(extracted_payload: dict[str, Any], field_name: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Return the best pages for a specific investor field."""
    field_info = FIELD_METADATA[field_name]
    aliases = field_info.get("aliases", [])
    query = " ".join(aliases)
    ranked_pages: list[tuple[float, dict[str, Any]]] = []

    for page in extracted_payload.get("pages", []):
        text = page.get("text", "")
        if not text:
            continue
        score = keyword_score(text, aliases) + token_cosine_score(text, query)
        if score <= 0:
            continue
        ranked_pages.append((score, page))

    ranked_pages.sort(key=lambda item: (-item[0], item[1].get("page_number", 0)))
    return [page for _, page in ranked_pages[:top_k]]


def discovery_summary(extracted_payload: dict[str, Any]) -> dict[str, Any]:
    """Show which investor categories appear to have evidence in the report."""
    summary: dict[str, Any] = {}
    for category, fields in INVESTOR_FIELD_GROUPS.items():
        category_summary = []
        for field_name in fields:
            ranked = rank_pages_for_field(extracted_payload, field_name, top_k=2)
            category_summary.append(
                {
                    "field": field_name,
                    "found": bool(ranked),
                    "candidate_pages": [page["page_number"] for page in ranked],
                    "sample_source_refs": [page["source_ref"] for page in ranked],
                }
            )
        summary[category] = category_summary
    return summary


def build_retrieval_context(extracted_payload: dict[str, Any], max_pages_per_field: int = 2) -> str:
    """Create the compact context block sent to the LLM prompts."""
    context_blocks: list[str] = []
    for category, fields in INVESTOR_FIELD_GROUPS.items():
        category_lines = [f"## {category.replace('_', ' ').title()}"]
        used_pages: set[int] = set()
        for field_name in fields:
            ranked = rank_pages_for_field(extracted_payload, field_name, top_k=max_pages_per_field)
            for page in ranked:
                page_number = page["page_number"]
                if page_number in used_pages:
                    continue
                used_pages.add(page_number)
                text = normalize_whitespace(page.get("text", ""))[:1800]
                category_lines.append(f"[Page {page_number}] {text}")
        if len(category_lines) > 1:
            context_blocks.append("\n".join(category_lines))

    if not context_blocks:
        for page in extracted_payload.get("pages", [])[:8]:
            context_blocks.append(f"[Page {page['page_number']}] {normalize_whitespace(page.get('text', ''))[:1800]}")
    return "\n\n".join(context_blocks)
