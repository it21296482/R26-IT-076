import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";
import api from "../lib/api";
import { INSIGHT_PREVIEW_STORAGE_KEY } from "./UserDashboardPage";

const sectionLabels = {
  company_overview: "Company overview",
  financial_performance: "Financial performance",
  financial_position: "Financial position",
  cash_flow: "Cash flow",
  investor_ratios: "Investor ratios",
  shareholder_information: "Shareholder information",
  risk_factors: "Risk factors",
  management_governance: "Management and governance",
  future_outlook: "Future outlook",
};

const viewOptions = [
  ["overview", "Overview"],
  ["financials", "Financials"],
  ["risks", "Risk & outlook"],
  ["evidence", "Evidence"],
];

const currencyFields = new Set([
  "revenue_turnover", "gross_profit", "operating_profit", "profit_before_tax", "profit_after_tax", "eps", "ebitda",
  "net_finance_cost", "tax_expense", "total_assets", "total_liabilities", "total_equity", "borrowings_debt",
  "cash_and_cash_equivalents", "inventory", "trade_receivables", "trade_payables", "operating_cash_flow",
  "investing_cash_flow", "financing_cash_flow", "free_cash_flow", "capital_expenditure", "stated_capital", "dividends",
  "market_price_per_share",
]);

const titleCase = (value) => value.replaceAll("_", " ").replaceAll(".", " / ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const displayValue = (value, field = "") => {
  // Currency formatting is display-only; percentages, ratios, and source wording remain unchanged.
  if (value === null || value === undefined || value === "") return "Not found";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "Not found";
  if (typeof value === "object") return JSON.stringify(value);
  if (!currencyFields.has(field)) return String(value);
  if (typeof value === "number") return `Rs. ${value.toLocaleString("en-LK")}`;

  const text = String(value).trim();
  if (/^lkr\b/i.test(text)) return text.replace(/^lkr\b\.?/i, "Rs.");
  if (/^rs\.?\s*/i.test(text)) return text.replace(/^rs\.?\s*/i, "Rs. ");
  if (/^[+-]?[\d,.]+(?:\s|$)/.test(text) && !/%|\btimes\b|\bshares?\b/i.test(text)) return `Rs. ${text}`;
  return text;
};

const readStoredPreview = () => {
  try {
    return JSON.parse(sessionStorage.getItem(INSIGHT_PREVIEW_STORAGE_KEY));
  } catch {
    return null;
  }
};

function FactSection({ facts, name }) {
  const entries = Object.entries(facts || {});

  return (
    <section className="border-t border-slate-200 pt-6 first:border-t-0 first:pt-0">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h3 className="text-lg font-semibold text-slate-950">{sectionLabels[name] || titleCase(name)}</h3>
        <span className="text-xs font-medium text-slate-400">{entries.length} fields</span>
      </div>
      <dl className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
        {entries.map(([field, value]) => {
          const unavailable = value === null || value === "" || (Array.isArray(value) && !value.length);
          return (
            <div className="min-w-0" key={field}>
              <dt className="text-xs font-medium text-slate-500">{titleCase(field)}</dt>
              <dd className={`mt-1 break-words text-sm leading-6 ${unavailable ? "text-slate-400" : "font-medium text-slate-800"}`}>
                {displayValue(value, field)}
              </dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}

function EmptyState({ message }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center text-sm leading-6 text-slate-500">
      {message}
    </div>
  );
}

function InsightPreviewPage() {
  const location = useLocation();
  const [previewRequest] = useState(location.state || readStoredPreview());
  const [stockUniverse, setStockUniverse] = useState([]);
  const [recentReports, setRecentReports] = useState([]);
  const [activeView, setActiveView] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadPreview = async () => {
      try {
        // Load company context and the user's report results together to reduce waiting time.
        const [{ data: stockData }, { data: reportData }] = await Promise.all([api.get("/stocks/universe"), api.get("/reports")]);
        setStockUniverse(stockData.stocks);
        setRecentReports(reportData.reports);
      } catch (requestError) {
        setError(requestError.response?.data?.message || "Unable to load the report insight.");
      } finally {
        setLoading(false);
      }
    };

    loadPreview();
  }, []);

  const selectedStock = stockUniverse.find((stock) => stock.symbol === previewRequest?.selectedSymbol);
  // Prefer the exact report requested during upload, then fall back to the latest report for the ticker.
  const latestReport =
    recentReports.find((report) => report._id === previewRequest?.reportId) ||
    recentReports.find((report) => report.stockSymbol === previewRequest?.selectedSymbol) ||
    null;
  const extraction = latestReport?.parsedExtraction || null;
  const facts = extraction?.extracted_facts || {};
  const insight = extraction?.investor_friendly_insight || null;
  const confidencePercent = Math.round(Math.max(0, Math.min(1, Number(extraction?.confidence_score) || 0)) * 100);
  const companyName = extraction?.metadata?.company_name || latestReport?.companyName || selectedStock?.companyName || "Selected company";
  const reportingYear = extraction?.metadata?.reporting_year || "Reporting year unavailable";
  const hasPreview = Boolean(previewRequest?.selectedSymbol);

  const performance = facts.financial_performance || {};
  const position = facts.financial_position || {};
  const keyFacts = [
    ["Revenue", "revenue_turnover", performance.revenue_turnover],
    ["Profit after tax", "profit_after_tax", performance.profit_after_tax],
    ["Earnings per share", "eps", performance.eps],
    ["Total assets", "total_assets", position.total_assets],
    ["Total liabilities", "total_liabilities", position.total_liabilities],
    ["Total equity", "total_equity", position.total_equity],
  ];

  const downloadReport = async () => {
    if (!extraction) return;
    // PDF code is loaded on demand so it does not slow the normal dashboard experience.
    const { downloadInvestorReportPdf } = await import("../lib/reportPdf");
    downloadInvestorReportPdf({ extraction, report: latestReport, ticker: previewRequest.selectedSymbol });
  };

  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader compact />

      <main className="shell space-y-6">
        <header className="flex flex-col gap-5 border-b border-slate-200 pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="eyebrow">Annual report intelligence</p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-950 md:text-4xl">Annual report insight</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Review the extracted investor facts, plain-language explanation, and supporting report evidence.
            </p>
          </div>
          <Link className="secondary-cta" to="/dashboard">Back to workspace</Link>
        </header>

        {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
        {loading && <div className="rounded-lg border border-slate-200 bg-white px-5 py-8 text-center text-sm text-slate-500">Loading report insight...</div>}

        {!hasPreview && !loading && (
          <EmptyState message="No analysis was selected. Return to the workspace and upload an annual report." />
        )}

        {hasPreview && !loading && (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_19rem]">
            <div className="min-w-0 space-y-6">
              <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-[#193b87] bg-[#081b49] px-6 py-6 text-white">
                  <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-300">
                        <span>{latestReport?.stockSymbol || previewRequest.selectedSymbol}</span>
                        <span>•</span>
                        <span>{reportingYear}</span>
                      </div>
                      <h2 className="mt-2 text-2xl font-semibold">{companyName}</h2>
                      <p className="mt-2 text-sm text-slate-300">{latestReport?.originalFilename || "No annual report uploaded"}</p>
                    </div>
                    <span className={`w-fit rounded-full border px-3 py-1.5 text-xs font-semibold ${latestReport?.processingStatus === "processed" ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-200" : latestReport?.processingStatus === "failed" ? "border-rose-300/30 bg-rose-300/10 text-rose-200" : "border-amber-300/30 bg-amber-300/10 text-amber-200"}`}>
                      {latestReport?.processingStatus || "No report"}
                    </span>
                  </div>
                </div>

                {extraction && (
                  <div className="grid divide-y divide-slate-200 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
                    <div className="px-6 py-4">
                      <p className="text-xs text-slate-500">Analysis method</p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">Beginner-friendly AI analysis</p>
                    </div>
                    <div className="px-6 py-4">
                      <p className="text-xs text-slate-500">Confidence</p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">{confidencePercent}%</p>
                    </div>
                    <div className="px-6 py-4">
                      <p className="text-xs text-slate-500">Verified citations</p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">{extraction.source_evidence?.length || 0}</p>
                    </div>
                  </div>
                )}
              </section>

              {latestReport?.processingStatus === "failed" && (
                <section className="rounded-lg border border-rose-200 bg-rose-50 p-5">
                  <h2 className="text-base font-semibold text-rose-900">Report processing failed</h2>
                  <p className="mt-2 text-sm leading-6 text-rose-700">{latestReport.extractionError || "The report could not be processed."}</p>
                  <p className="mt-3 text-xs text-rose-600">Correct the configuration, then return to the workspace and run the report again.</p>
                </section>
              )}

              {!latestReport && <EmptyState message="No annual report is attached to this analysis." />}

              {extraction && (
                <>
                  {/* Tabs separate summary, detailed facts, risks, and evidence to reduce information overload. */}
                  <nav aria-label="Report result views" className="flex gap-1 overflow-x-auto rounded-lg border border-slate-200 bg-slate-100 p-1">
                    {viewOptions.map(([value, label]) => (
                      <button
                        className={`min-w-fit flex-1 rounded-md px-4 py-2.5 text-sm font-semibold transition ${activeView === value ? "bg-white text-[#1d4aa8] shadow-sm" : "text-slate-500 hover:text-[#1d4aa8]"}`}
                        key={value}
                        onClick={() => setActiveView(value)}
                        type="button"
                      >
                        {label}
                      </button>
                    ))}
                  </nav>

                  {activeView === "overview" && (
                    <div className="space-y-6">
                      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                        <p className="text-xs font-semibold uppercase text-blue-700">Beginner-friendly explanation</p>
                        <p className="mt-3 text-base leading-7 text-slate-700">{insight?.summary || "No summary was generated."}</p>
                        <div className="mt-6 border-t border-slate-200 pt-5">
                          <p className="text-xs font-medium text-slate-500">Risk explanation</p>
                          <p className="mt-2 text-sm leading-6 text-slate-700">{insight?.risk_level_explanation || "Not available"}</p>
                        </div>
                      </section>

                      <section className="grid gap-4 md:grid-cols-2">
                        <article className="rounded-lg border border-emerald-200 bg-emerald-50 p-5">
                          <h3 className="font-semibold text-emerald-950">Key strengths</h3>
                          <ul className="mt-3 space-y-2 text-sm leading-6 text-emerald-900">
                            {(insight?.key_strengths || []).map((item) => <li key={item}>• {item}</li>)}
                            {!insight?.key_strengths?.length && <li>No strengths were identified.</li>}
                          </ul>
                        </article>
                        <article className="rounded-lg border border-amber-200 bg-amber-50 p-5">
                          <h3 className="font-semibold text-amber-950">Key concerns</h3>
                          <ul className="mt-3 space-y-2 text-sm leading-6 text-amber-900">
                            {(insight?.key_concerns || []).map((item) => <li key={item}>• {item}</li>)}
                            {!insight?.key_concerns?.length && <li>No concerns were identified.</li>}
                          </ul>
                        </article>
                      </section>

                      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                        <h3 className="text-lg font-semibold text-slate-950">Key financial facts</h3>
                        <dl className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                          {keyFacts.map(([label, field, value]) => (
                            <div className="rounded-md bg-slate-50 p-4" key={label}>
                              <dt className="text-xs text-slate-500">{label}</dt>
                              <dd className="mt-1 break-words text-sm font-semibold leading-6 text-slate-900">{displayValue(value, field)}</dd>
                            </div>
                          ))}
                        </dl>
                      </section>
                    </div>
                  )}

                  {activeView === "financials" && (
                    <section className="space-y-7 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                      {["company_overview", "financial_performance", "financial_position", "cash_flow", "investor_ratios", "shareholder_information"].map((section) => (
                        <FactSection facts={facts[section]} key={section} name={section} />
                      ))}
                    </section>
                  )}

                  {activeView === "risks" && (
                    <section className="space-y-7 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                      {["risk_factors", "management_governance", "future_outlook"].map((section) => (
                        <FactSection facts={facts[section]} key={section} name={section} />
                      ))}
                    </section>
                  )}

                  {activeView === "evidence" && (
                    <div className="space-y-6">
                      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                        <h3 className="text-lg font-semibold text-slate-950">Verified report evidence</h3>
                        <p className="mt-1 text-sm text-slate-500">These quotations were checked against the uploaded annual report.</p>
                        <div className="mt-5 space-y-3">
                          {(extraction.source_evidence || []).map((item, index) => (
                            <blockquote className="rounded-md border-l-4 border-blue-600 bg-slate-50 p-4" key={`${item.source_id}-${item.field}-${index}`}>
                              <p className="text-sm leading-6 text-slate-700">“{item.source_quote}”</p>
                              <footer className="mt-2 text-xs text-slate-500">{titleCase(item.field || "Report fact")} · {item.source_id}{item.page_number ? ` · Page ${item.page_number}` : ""}</footer>
                            </blockquote>
                          ))}
                          {!extraction.source_evidence?.length && <EmptyState message="No verified quotations are available. Review the supporting report passages below." />}
                        </div>
                      </section>

                      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                        <h3 className="text-lg font-semibold text-slate-950">Supporting report passages</h3>
                        <div className="mt-5 divide-y divide-slate-200">
                          {(latestReport.ragSources || []).map((source) => (
                            <details className="py-4" key={source.sourceId || source.chunkId}>
                              <summary className="flex cursor-pointer items-center justify-between gap-4 text-sm font-semibold text-slate-800">
                                <span>{source.sourceId || source.chunkId}</span>
                                <span className="text-xs font-normal text-slate-500">{source.estimatedPage ? `Page ${source.estimatedPage}` : "Page unavailable"}</span>
                              </summary>
                              <p className="mt-3 text-sm leading-6 text-slate-600">{source.snippet}</p>
                            </details>
                          ))}
                        </div>
                      </section>
                    </div>
                  )}
                </>
              )}
            </div>

            <aside className="space-y-5 lg:sticky lg:top-28 lg:self-start">
              <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="font-semibold text-slate-950">Report details</h2>
                <dl className="mt-4 space-y-4 text-sm">
                  <div><dt className="text-xs text-slate-500">Company</dt><dd className="mt-1 font-medium text-slate-800">{companyName}</dd></div>
                  <div><dt className="text-xs text-slate-500">Ticker</dt><dd className="mt-1 font-medium text-slate-800">{latestReport?.stockSymbol || previewRequest.selectedSymbol}</dd></div>
                  <div><dt className="text-xs text-slate-500">Analysis type</dt><dd className="mt-1 font-medium text-slate-800">Beginner-friendly investor explanation</dd></div>
                  <div><dt className="text-xs text-slate-500">Report passages reviewed</dt><dd className="mt-1 font-medium text-slate-800">{latestReport?.ragSelectedCount || 0} selected from {latestReport?.ragChunkCount || 0}</dd></div>
                </dl>
                {extraction && <button className="mt-5 w-full rounded-md bg-[#1d4aa8] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#163d8d]" onClick={downloadReport} type="button">Download PDF</button>}
              </section>

              {extraction && (
                <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="font-semibold text-slate-950">Information not found</h2>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{extraction.missing_fields?.length || 0}</span>
                  </div>
                  <div className="mt-4 max-h-64 space-y-2 overflow-y-auto pr-1">
                    {(extraction.missing_fields || []).map((field) => <p className="text-xs leading-5 text-slate-500" key={field}>{titleCase(field)}</p>)}
                    {!extraction.missing_fields?.length && <p className="text-sm text-slate-500">All expected information was found.</p>}
                  </div>
                </section>
              )}

              <p className="px-1 text-xs leading-5 text-slate-500">
                {insight?.non_advisory_note || "This output is informational and is not financial advice."}
              </p>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}

export default InsightPreviewPage;
