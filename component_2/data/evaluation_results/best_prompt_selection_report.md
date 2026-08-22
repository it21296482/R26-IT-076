# Best Prompt Selection Report

Selected prompt: **prompt_08 - Beginner Investor Explanation Prompt**

Average final score: **0.1693**

## How The Best Prompt Was Calculated

Each annual report first gets an expected source-grounded output from the extracted PDF text. Then each of the 10 prompt outputs is compared against that expected output.

Formula: `final_score = 0.25 * coverage_score + 0.20 * numeric_accuracy_score + 0.20 * semantic_similarity_score + 0.20 * source_faithfulness_score + 0.15 * investor_relevance_score - hallucination_penalty`

## Score Meaning

- `coverage_score`: how many expected investor fields the prompt extracted.
- `numeric_accuracy_score`: how well numeric values match after unit/currency normalization.
- `semantic_similarity_score`: similarity between expected values and prompt output values.
- `source_faithfulness_score`: whether cited source quotes actually exist in the extracted PDF text.
- `investor_relevance_score`: whether the output focuses on investor-useful categories.
- `hallucination_penalty`: penalty for unsupported evidence or missing evidence.

## Average Score Breakdown For Selected Prompt

- `coverage_score`: 0.9342
- `numeric_accuracy_score`: 0.0619
- `semantic_similarity_score`: 0.1168
- `source_faithfulness_score`: 0.0
- `investor_relevance_score`: 1.0
- `hallucination_penalty`: 0.25
- `final_score`: 0.1693

## Ranking Of All 10 Prompts

| Rank | Prompt ID | Prompt Name | Similarity | Final Score | Reports Evaluated |
| --- | --- | --- | --- | --- | --- |
| 1 | prompt_08 | Beginner Investor Explanation Prompt | 0.1168 | 0.1693 | 6 |
| 2 | prompt_10 | Hybrid Best-Practice Prompt | 0.106 | 0.1673 | 6 |
| 3 | prompt_07 | Risk-Focused Investor Prompt | 0.1052 | 0.1645 | 6 |
| 4 | prompt_02 | Role-Based Financial Analyst Prompt | 0.1047 | 0.1634 | 6 |
| 5 | prompt_01 | Basic Extraction Prompt | 0.1075 | 0.1619 | 6 |
| 6 | prompt_06 | Ratio-Aware Prompt | 0.0983 | 0.1613 | 6 |
| 7 | prompt_04 | Source-Grounded Evidence Prompt | 0.1064 | 0.1596 | 6 |
| 8 | prompt_05 | Chain-of-Verification Prompt | 0.1138 | 0.1573 | 6 |
| 9 | prompt_03 | JSON Schema-Constrained Prompt | 0.1233 | 0.1555 | 6 |
| 10 | prompt_09 | Few-Shot Prompt | 0.1179 | 0.1376 | 6 |

## Prompt Text To Reuse

```text
Extract report-backed facts and explain them in simple language for beginner investors.
Keep explanations factual, concise, and non-advisory.
Return only valid JSON with this schema:
{
  "metadata": {
    "pdf_name": "",
    "company_name": "",
    "reporting_year": "",
    "prompt_id": "",
    "model": "",
    "generated_at": ""
  },
  "extracted_facts": {
    "company_overview": {
      "company_name": null,
      "reporting_year": null,
      "business_segments": null,
      "principal_activities": null,
      "sector_industry": null,
      "subsidiaries_associates": null
    },
    "financial_performance": {
      "revenue_turnover": null,
      "gross_profit": null,
      "operating_profit": null,
      "profit_before_tax": null,
      "profit_after_tax": null,
      "eps": null,
      "ebitda": null,
      "net_finance_cost": null,
      "tax_expense": null
    },
    "financial_position": {
      "total_assets": null,
      "total_liabilities": null,
      "total_equity": null,
      "borrowings_debt": null,
      "cash_and_cash_equivalents": null,
      "inventory": null,
      "trade_receivables": null,
      "trade_payables": null
    },
    "cash_flow": {
      "operating_cash_flow": null,
      "investing_cash_flow": null,
      "financing_cash_flow": null,
      "free_cash_flow": null,
      "capital_expenditure": null
    },
    "investor_ratios": {
      "gross_profit_margin": null,
      "net_profit_margin": null,
      "current_ratio": null,
      "debt_to_equity_ratio": null,
      "return_on_equity": null,
      "return_on_assets": null,
      "eps_ratio_reference": null,
      "dividend_payout_ratio": null
    },
    "shareholder_information": {
      "stated_capital": null,
      "number_of_shares": null,
      "major_shareholders": null,
      "public_holding_percentage": null,
      "dividends": null,
      "market_price_per_share": null
    },
    "risk_factors": {
      "liquidity_risk": null,
      "credit_risk": null,
      "market_risk": null,
      "interest_rate_risk": null,
      "foreign_exchange_risk": null,
      "operational_risk": null,
      "regulatory_risk": null,
      "going_concern_concerns": null,
      "litigation_contingencies": null
    },
    "management_governance": {
      "board_changes": null,
      "auditor_opinion": null,
      "related_party_transactions": null,
      "corporate_governance_statements": null,
      "director_responsibility_statement": null
    },
    "future_outlook": {
      "chairman_ceo_outlook": null,
      "expansion_plans": null,
      "expected_challenges": null,
      "strategy": null,
      "forward_looking_statements": null
    }
  },
  "investor_friendly_insight": {
    "summary": "",
    "key_strengths": [],
    "key_concerns": [],
    "risk_level_explanation": "",
    "non_advisory_note": "This is an informational summary only and not financial advice."
  },
  "source_evidence": [],
  "missing_fields": [],
  "confidence_score": 0.0
}
```