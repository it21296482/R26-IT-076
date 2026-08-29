"""Shared investor field definitions and standard JSON schema.

The schema is the contract used by all prompts, evaluation, and final reports.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any


INVESTOR_FIELD_GROUPS: OrderedDict[str, OrderedDict[str, dict[str, Any]]] = OrderedDict(
    [
        (
            "company_overview",
            OrderedDict(
                [
                    ("company_name", {"aliases": ["company name", "plc", "limited"], "numeric": False}),
                    ("reporting_year", {"aliases": ["financial year ended", "year ended", "annual report"], "numeric": False}),
                    ("business_segments", {"aliases": ["business segments", "segments", "segment information"], "numeric": False}),
                    ("principal_activities", {"aliases": ["principal activities", "nature of business"], "numeric": False}),
                    ("sector_industry", {"aliases": ["sector", "industry"], "numeric": False}),
                    ("subsidiaries_associates", {"aliases": ["subsidiaries", "associates"], "numeric": False}),
                ]
            ),
        ),
        (
            "financial_performance",
            OrderedDict(
                [
                    ("revenue_turnover", {"aliases": ["revenue", "turnover", "total income"], "numeric": True}),
                    ("gross_profit", {"aliases": ["gross profit"], "numeric": True}),
                    ("operating_profit", {"aliases": ["operating profit", "operating income"], "numeric": True}),
                    ("profit_before_tax", {"aliases": ["profit before tax", "pbt"], "numeric": True}),
                    ("profit_after_tax", {"aliases": ["profit after tax", "profit for the year", "net profit"], "numeric": True}),
                    ("eps", {"aliases": ["earnings per share", "basic earnings per share", "diluted earnings per share", "eps"], "numeric": True}),
                    ("ebitda", {"aliases": ["ebitda"], "numeric": True}),
                    ("net_finance_cost", {"aliases": ["net finance cost", "finance cost", "net finance expense"], "numeric": True}),
                    ("tax_expense", {"aliases": ["tax expense", "income tax expense"], "numeric": True}),
                ]
            ),
        ),
        (
            "financial_position",
            OrderedDict(
                [
                    ("total_assets", {"aliases": ["total assets"], "numeric": True}),
                    ("total_liabilities", {"aliases": ["total liabilities"], "numeric": True}),
                    ("total_equity", {"aliases": ["total equity", "equity attributable"], "numeric": True}),
                    ("borrowings_debt", {"aliases": ["borrowings", "debt", "interest bearing loans"], "numeric": True}),
                    ("cash_and_cash_equivalents", {"aliases": ["cash and cash equivalents"], "numeric": True}),
                    ("inventory", {"aliases": ["inventory", "inventories"], "numeric": True}),
                    ("trade_receivables", {"aliases": ["trade receivables", "receivables"], "numeric": True}),
                    ("trade_payables", {"aliases": ["trade payables", "payables"], "numeric": True}),
                ]
            ),
        ),
        (
            "cash_flow",
            OrderedDict(
                [
                    ("operating_cash_flow", {"aliases": ["operating cash flow", "net cash from operating activities", "cash flows from operating activities"], "numeric": True}),
                    ("investing_cash_flow", {"aliases": ["investing cash flow", "net cash used in investing activities"], "numeric": True}),
                    ("financing_cash_flow", {"aliases": ["financing cash flow", "net cash from financing activities"], "numeric": True}),
                    ("free_cash_flow", {"aliases": ["free cash flow"], "numeric": True, "derived": True}),
                    ("capital_expenditure", {"aliases": ["capital expenditure", "capex", "purchase of property plant and equipment"], "numeric": True}),
                ]
            ),
        ),
        (
            "investor_ratios",
            OrderedDict(
                [
                    ("gross_profit_margin", {"aliases": ["gross profit margin"], "numeric": True, "ratio": True}),
                    ("net_profit_margin", {"aliases": ["net profit margin"], "numeric": True, "ratio": True}),
                    ("current_ratio", {"aliases": ["current ratio"], "numeric": True, "ratio": True}),
                    ("debt_to_equity_ratio", {"aliases": ["debt to equity ratio", "debt-to-equity"], "numeric": True, "ratio": True}),
                    ("return_on_equity", {"aliases": ["return on equity", "roe"], "numeric": True, "ratio": True}),
                    ("return_on_assets", {"aliases": ["return on assets", "roa"], "numeric": True, "ratio": True}),
                    ("eps_ratio_reference", {"aliases": ["earnings per share", "eps"], "numeric": True}),
                    ("dividend_payout_ratio", {"aliases": ["dividend payout ratio"], "numeric": True, "ratio": True}),
                ]
            ),
        ),
        (
            "shareholder_information",
            OrderedDict(
                [
                    ("stated_capital", {"aliases": ["stated capital", "share capital"], "numeric": True}),
                    ("number_of_shares", {"aliases": ["number of shares", "issued shares", "ordinary shares"], "numeric": True}),
                    ("major_shareholders", {"aliases": ["major shareholders", "top shareholders"], "numeric": False}),
                    ("public_holding_percentage", {"aliases": ["public holding", "public float"], "numeric": True}),
                    ("dividends", {"aliases": ["dividend", "dividends paid"], "numeric": True}),
                    ("market_price_per_share", {"aliases": ["market price per share", "share price"], "numeric": True}),
                ]
            ),
        ),
        (
            "risk_factors",
            OrderedDict(
                [
                    ("liquidity_risk", {"aliases": ["liquidity risk"], "numeric": False}),
                    ("credit_risk", {"aliases": ["credit risk"], "numeric": False}),
                    ("market_risk", {"aliases": ["market risk"], "numeric": False}),
                    ("interest_rate_risk", {"aliases": ["interest rate risk"], "numeric": False}),
                    ("foreign_exchange_risk", {"aliases": ["foreign exchange risk", "currency risk"], "numeric": False}),
                    ("operational_risk", {"aliases": ["operational risk"], "numeric": False}),
                    ("regulatory_risk", {"aliases": ["regulatory risk", "compliance risk"], "numeric": False}),
                    ("going_concern_concerns", {"aliases": ["going concern"], "numeric": False}),
                    ("litigation_contingencies", {"aliases": ["litigation", "contingencies", "contingent liabilities"], "numeric": False}),
                ]
            ),
        ),
        (
            "management_governance",
            OrderedDict(
                [
                    ("board_changes", {"aliases": ["board changes", "appointment", "resignation"], "numeric": False}),
                    ("auditor_opinion", {"aliases": ["auditor opinion", "independent auditors' report", "true and fair view", "in our opinion"], "numeric": False}),
                    ("related_party_transactions", {"aliases": ["related party transactions"], "numeric": False}),
                    ("corporate_governance_statements", {"aliases": ["corporate governance"], "numeric": False}),
                    ("director_responsibility_statement", {"aliases": ["director responsibility", "statement of directors"], "numeric": False}),
                ]
            ),
        ),
        (
            "future_outlook",
            OrderedDict(
                [
                    ("chairman_ceo_outlook", {"aliases": ["chairman's statement", "ceo review", "future outlook", "looking ahead"], "numeric": False}),
                    ("expansion_plans", {"aliases": ["expansion plans", "expansion"], "numeric": False}),
                    ("expected_challenges", {"aliases": ["expected challenges", "challenges ahead"], "numeric": False}),
                    ("strategy", {"aliases": ["strategy", "strategic priorities"], "numeric": False}),
                    ("forward_looking_statements", {"aliases": ["forward-looking", "future prospects", "outlook"], "numeric": False}),
                ]
            ),
        ),
    ]
)


INVESTOR_SUMMARY_FIELDS = [
    "key_positives",
    "key_concerns",
    "performance_trend",
    "risk_summary",
    "simple_explanation",
]


def ordered_field_names() -> list[str]:
    """Return all expected investor field names in schema order."""
    names: list[str] = []
    for fields in INVESTOR_FIELD_GROUPS.values():
        names.extend(fields.keys())
    return names


def build_standard_output_schema() -> OrderedDict[str, Any]:
    """Build the JSON schema every prompt must follow."""
    extracted_facts = OrderedDict()
    for category, fields in INVESTOR_FIELD_GROUPS.items():
        extracted_facts[category] = OrderedDict((field, None) for field in fields)

    schema = OrderedDict(
        [
            (
                "metadata",
                OrderedDict(
                    [
                        ("pdf_name", ""),
                        ("company_name", ""),
                        ("reporting_year", ""),
                        ("prompt_id", ""),
                        ("model", ""),
                        ("generated_at", ""),
                    ]
                ),
            ),
            ("extracted_facts", extracted_facts),
            (
                "investor_friendly_insight",
                OrderedDict(
                    [
                        ("summary", ""),
                        ("key_strengths", []),
                        ("key_concerns", []),
                        ("risk_level_explanation", ""),
                        ("non_advisory_note", "This is an informational summary only and not financial advice."),
                    ]
                ),
            ),
            ("source_evidence", []),
            ("missing_fields", []),
            ("confidence_score", 0.0),
        ]
    )
    return schema


def default_prompt_output() -> OrderedDict[str, Any]:
    """Return a blank prompt output template."""
    return build_standard_output_schema()


def now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def deep_copy_template() -> dict[str, Any]:
    """Return a mutable deep copy of the standard schema."""
    return json.loads(json.dumps(build_standard_output_schema()))
