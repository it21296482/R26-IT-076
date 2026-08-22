const path = require("path");

const BEST_PROMPT_ID = "prompt_08";
const BEST_PROMPT_NAME = "Beginner Investor Explanation Prompt";
const BEST_PROMPT_FILE = "best_prompt_to_use.txt";
const BEST_PROMPT_PATH = path.resolve(
  __dirname,
  "../../../component_2/data/evaluation_results/best_prompt_to_use.txt"
);

// This template mirrors the common schema used to compare all 10 research prompts.
// Keeping one schema makes prompt scores comparable and gives the frontend a stable contract.
const EXTRACTION_TEMPLATE = {
  metadata: { pdf_name: "", company_name: "", reporting_year: "", prompt_id: "", model: "", generated_at: "" },
  extracted_facts: {
    company_overview: { company_name: null, reporting_year: null, business_segments: null, principal_activities: null, sector_industry: null, subsidiaries_associates: null },
    financial_performance: { revenue_turnover: null, gross_profit: null, operating_profit: null, profit_before_tax: null, profit_after_tax: null, eps: null, ebitda: null, net_finance_cost: null, tax_expense: null },
    financial_position: { total_assets: null, total_liabilities: null, total_equity: null, borrowings_debt: null, cash_and_cash_equivalents: null, inventory: null, trade_receivables: null, trade_payables: null },
    cash_flow: { operating_cash_flow: null, investing_cash_flow: null, financing_cash_flow: null, free_cash_flow: null, capital_expenditure: null },
    investor_ratios: { gross_profit_margin: null, net_profit_margin: null, current_ratio: null, debt_to_equity_ratio: null, return_on_equity: null, return_on_assets: null, eps_ratio_reference: null, dividend_payout_ratio: null },
    shareholder_information: { stated_capital: null, number_of_shares: null, major_shareholders: null, public_holding_percentage: null, dividends: null, market_price_per_share: null },
    risk_factors: { liquidity_risk: null, credit_risk: null, market_risk: null, interest_rate_risk: null, foreign_exchange_risk: null, operational_risk: null, regulatory_risk: null, going_concern_concerns: null, litigation_contingencies: null },
    management_governance: { board_changes: null, auditor_opinion: null, related_party_transactions: null, corporate_governance_statements: null, director_responsibility_statement: null },
    future_outlook: { chairman_ceo_outlook: null, expansion_plans: null, expected_challenges: null, strategy: null, forward_looking_statements: null },
  },
  investor_friendly_insight: {
    summary: "",
    key_strengths: [],
    key_concerns: [],
    risk_level_explanation: "",
    non_advisory_note: "This is an informational summary only and not financial advice.",
  },
  source_evidence: [],
  missing_fields: [],
  confidence_score: 0,
};

module.exports = { BEST_PROMPT_FILE, BEST_PROMPT_ID, BEST_PROMPT_NAME, BEST_PROMPT_PATH, EXTRACTION_TEMPLATE };
