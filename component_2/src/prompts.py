"""Ten prompt strategies used for the benchmark.

Every strategy receives the same report context and must produce the same JSON
schema, allowing fair comparison of prompt design quality.
"""

from __future__ import annotations

import json
from collections import OrderedDict

from .schemas import build_standard_output_schema


STANDARD_SCHEMA = json.dumps(build_standard_output_schema(), ensure_ascii=False, indent=2)


def prompt_definitions() -> list[dict[str, str]]:
    """Return the 10 prompt strategies used in the benchmark."""
    return [
        {
            "prompt_id": "prompt_01",
            "prompt_name": "Basic Extraction Prompt",
            "prompt_text": f"""Extract investor-related information from the annual report context.
Return only valid JSON matching this exact schema:
{STANDARD_SCHEMA}
Use only information present in the report context.
Do not provide investment advice.""",
        },
        {
            "prompt_id": "prompt_02",
            "prompt_name": "Role-Based Financial Analyst Prompt",
            "prompt_text": f"""You are a financial analyst preparing an investor-education summary from an annual report.
Extract source-grounded facts useful to retail investors and return only valid JSON with this schema:
{STANDARD_SCHEMA}
Do not recommend buy, sell, or hold.""",
        },
        {
            "prompt_id": "prompt_03",
            "prompt_name": "JSON Schema-Constrained Prompt",
            "prompt_text": f"""Return only JSON. No markdown. No commentary.
Every output must follow this schema exactly:
{STANDARD_SCHEMA}
Leave missing data as null and add those field names to missing_fields.""",
        },
        {
            "prompt_id": "prompt_04",
            "prompt_name": "Source-Grounded Evidence Prompt",
            "prompt_text": f"""Extract investor-related information and include page-level evidence in source_evidence for every important fact.
Return only valid JSON with this exact schema:
{STANDARD_SCHEMA}
Every material fact must cite a page number and short source quote from the provided report context.""",
        },
        {
            "prompt_id": "prompt_05",
            "prompt_name": "Chain-of-Verification Prompt",
            "prompt_text": f"""Step 1: extract candidate facts.
Step 2: verify each candidate against the report context.
Step 3: remove any fact that cannot be verified.
Step 4: return only valid JSON with this schema:
{STANDARD_SCHEMA}
Do not hallucinate.""",
        },
        {
            "prompt_id": "prompt_06",
            "prompt_name": "Ratio-Aware Prompt",
            "prompt_text": f"""Extract investor facts and calculate ratios only when the required source values are present.
If a ratio cannot be calculated from the provided context, leave it null and list it in missing_fields.
Return only valid JSON with this schema:
{STANDARD_SCHEMA}""",
        },
        {
            "prompt_id": "prompt_07",
            "prompt_name": "Risk-Focused Investor Prompt",
            "prompt_text": f"""Prioritize risk factors, liabilities, debt, cash flow quality, governance issues, and auditor opinion.
Still complete the full schema below and return only valid JSON:
{STANDARD_SCHEMA}
Keep the summary investor-friendly and non-advisory.""",
        },
        {
            "prompt_id": "prompt_08",
            "prompt_name": "Beginner Investor Explanation Prompt",
            "prompt_text": f"""Extract report-backed facts and explain them in simple language for beginner investors.
Keep explanations factual, concise, and non-advisory.
Return only valid JSON with this schema:
{STANDARD_SCHEMA}""",
        },
        {
            "prompt_id": "prompt_09",
            "prompt_name": "Few-Shot Prompt",
            "prompt_text": f"""Example field:
{{
  "source_evidence": [
    {{
      "field": "revenue_turnover",
      "value": "Rs. 12,500 million",
      "page_number": 74,
      "source_quote": "Revenue for the year amounted to Rs. 12,500 million."
    }}
  ]
}}

Example missing field:
{{
  "missing_fields": ["free_cash_flow"]
}}

Now extract the provided annual report context and return only valid JSON with this schema:
{STANDARD_SCHEMA}""",
        },
        {
            "prompt_id": "prompt_10",
            "prompt_name": "Hybrid Best-Practice Prompt",
            "prompt_text": f"""You are a source-grounded financial analyst.
Rules:
- return only valid JSON
- follow the schema exactly
- use page references and source quotes
- do not hallucinate
- calculate ratios only when source values exist
- explain results for retail investors without giving financial advice

Schema:
{STANDARD_SCHEMA}""",
        },
    ]
