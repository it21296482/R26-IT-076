import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";
import api from "../lib/api";
import { INSIGHT_PREVIEW_STORAGE_KEY } from "./UserDashboardPage";

const insightCards = [
  ["Trend signal", "Positive momentum pattern ready for analysis."],
  ["Anomaly check", "Volume and price behavior scanned for unusual movement."],
  ["Sentiment pulse", "Market context prepared for news and event interpretation."],
  ["Risk indicator", "Confidence and uncertainty summarized for decision support."],
];

const factorChips = ["Price momentum", "Report context", "Sentiment signal"];
const componentStatusStyles = {
  ready: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100",
  queued: "border-amber-300/25 bg-amber-300/10 text-amber-100",
  pending: "border-slate-300/20 bg-white/8 text-slate-200",
};

const readStoredPreview = () => {
  try {
    return JSON.parse(sessionStorage.getItem(INSIGHT_PREVIEW_STORAGE_KEY));
  } catch {
    return null;
  }
};

function InsightPreviewPage() {
  const location = useLocation();
  const [previewRequest] = useState(location.state || readStoredPreview());
  const [stockUniverse, setStockUniverse] = useState([]);
  const [recentReports, setRecentReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadPreview = async () => {
      try {
        const [{ data: stockData }, { data: reportData }] = await Promise.all([api.get("/stocks/universe"), api.get("/reports")]);
        setStockUniverse(stockData.stocks);
        setRecentReports(reportData.reports);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to load the insight preview.");
      } finally {
        setLoading(false);
      }
    };

    loadPreview();
  }, []);

  const selectedStock = stockUniverse.find((stock) => stock.symbol === previewRequest?.selectedSymbol);
  const latestReport =
    recentReports.find((report) => report._id === previewRequest?.reportId) ||
    recentReports.find((report) => report.stockSymbol === previewRequest?.selectedSymbol) ||
    null;
  const hasPreview = Boolean(previewRequest?.selectedSymbol);

  const pipelineStatus = [
    ["Stock data", selectedStock ? "Ready" : "Waiting"],
    ["Report intake", latestReport?.processingStatus || "Optional"],
    ["Sentiment", hasPreview ? "Prepared" : "Pending"],
    ["XAI insight", hasPreview ? "Preparing" : "Waiting"],
  ];

  const componentOutputs = useMemo(
    () => [
      {
        code: "01",
        title: "Stock Data Component",
        accent: "from-cyan-300/35 via-sky-300/10 to-transparent",
        status: selectedStock ? "Available" : "Waiting",
        tone: selectedStock ? "ready" : "pending",
        output: selectedStock?.symbol || "No stock selected",
        input: selectedStock?.companyName || "Company selection required",
        evidence: selectedStock ? `${selectedStock.recordCount} market records checked.` : "Return to controls and select a company.",
      },
      {
        code: "02",
        title: "Financial Report Component",
        accent: "from-amber-300/35 via-orange-300/10 to-transparent",
        status: latestReport ? latestReport.processingStatus : "Optional",
        tone: latestReport ? "queued" : "pending",
        output: latestReport?.originalFilename || "No report uploaded",
        input: latestReport?.companyName || selectedStock?.companyName || "PDF report optional",
        evidence: latestReport ? "Report is queued for document parsing." : "Preview generated without a financial report.",
      },
      {
        code: "03",
        title: "Sentiment Component",
        accent: "from-fuchsia-300/30 via-rose-300/10 to-transparent",
        status: hasPreview ? "Prepared" : "Pending",
        tone: hasPreview ? "ready" : "pending",
        output: hasPreview ? "Market sentiment signal prepared" : "Not generated",
        input: selectedStock?.companyName || "Company selection required",
        evidence: hasPreview ? "Market context prepared as a separate signal." : "Generate preview to prepare this output.",
      },
      {
        code: "04",
        title: "Risk Component",
        accent: "from-emerald-300/30 via-teal-300/10 to-transparent",
        status: hasPreview ? "Calculated" : "Pending",
        tone: hasPreview ? "ready" : "pending",
        output: hasPreview ? "Moderate risk level" : "Not generated",
        input: selectedStock?.symbol || "Stock data required",
        evidence: hasPreview ? "Uncertainty is separated from the final insight." : "Risk output appears after setup.",
      },
      {
        code: "05",
        title: "Explainable AI Component",
        accent: "from-blue-300/35 via-indigo-300/10 to-transparent",
        status: hasPreview ? "Prepared" : "Waiting",
        tone: hasPreview ? "ready" : "pending",
        output: hasPreview ? "Top contributing factors identified" : "Not generated",
        input: "Stock, report, sentiment, and risk outputs",
        evidence: hasPreview ? "Key factors are ready for explanation." : "XAI output appears after preview generation.",
      },
    ],
    [hasPreview, latestReport, selectedStock]
  );

  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader compact />

      <main className="shell space-y-8">
        <section className="surface-panel fade-rise">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div>
              <p className="eyebrow">Visualization dashboard</p>
              <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
                Module output visualization.
              </h1>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
                Review stock data, financial report intake, sentiment, risk, and explainable AI outputs as separate
                visual modules before the final investment-support view.
              </p>
            </div>
            <Link className="secondary-cta" to="/dashboard">
              Back to controls
            </Link>
          </div>
        </section>

        {!hasPreview && !loading && (
          <section className="surface-panel text-center">
            <p className="eyebrow !text-slate-500">No preview found</p>
            <h2 className="mt-3 text-3xl font-semibold text-slate-950">Start an analysis first.</h2>
            <p className="mx-auto mt-4 max-w-xl text-base leading-8 text-slate-600">
              This visualization dashboard opens after you select a stock and click Start Analysis.
            </p>
            <Link className="primary-cta mt-6" to="/dashboard">
              Go to controls
            </Link>
          </section>
        )}

        {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
        {loading && <p className="text-sm text-slate-500">Loading insight preview...</p>}

        {hasPreview && !loading && (
          <section className="market-hero relative overflow-hidden p-6 fade-rise-delay-1 md:p-8">
            <div className="market-orb absolute -right-16 bottom-0 h-44 w-44 opacity-75" />
            <div className="relative z-10 space-y-6">
              <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr] lg:items-stretch">
                <div className="rounded-[28px] border border-white/10 bg-white/8 p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="eyebrow !text-blue-100">Live insight board</p>
                      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">
                        {selectedStock?.companyName || "Selected company"}
                      </h2>
                    </div>
                    <div className="rounded-full border border-white/10 bg-emerald-300/15 px-4 py-2 text-sm font-semibold text-emerald-100">
                      Confidence 82%
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Ticker</p>
                      <p className="mt-2 text-lg font-semibold text-white">{selectedStock?.symbol || previewRequest.selectedSymbol}</p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Records</p>
                      <p className="mt-2 text-lg font-semibold text-white">{selectedStock?.recordCount || "Pending"}</p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Risk watch</p>
                      <p className="mt-2 text-lg font-semibold text-white">Moderate</p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Report context</p>
                      <p className="mt-2 text-lg font-semibold text-white">{latestReport?.processingStatus || "Optional"}</p>
                    </div>
                  </div>
                </div>

                <div className="overflow-hidden rounded-[28px] border border-white/10 bg-white/8 p-3">
                  <img
                    alt="Bull and bear market analysis"
                    className="h-64 w-full rounded-[22px] object-cover lg:h-full"
                    src="/assets/360_F_754695855_hkDMu3QQ8Yu1kQZbyHHwgokSpmkXqqff.jpg"
                  />
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                {pipelineStatus.map(([label, status], index) => (
                  <div className="pipeline-step border-white/10 bg-white/8 p-4" key={label}>
                    <p className="text-xs font-semibold text-blue-100/70">0{index + 1}</p>
                    <p className="mt-3 text-[10px] uppercase tracking-[0.2em] text-blue-100/50">{label}</p>
                    <p className="mt-1 text-sm font-semibold text-white">{status}</p>
                  </div>
                ))}
              </div>

              <div className="relative overflow-hidden rounded-[34px] border border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.14),rgba(255,255,255,0.06))] p-6 shadow-[0_28px_80px_rgba(3,10,35,0.22)] md:p-8">
                <div className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-sky-300/15 blur-3xl" />
                <div className="absolute -bottom-28 left-10 h-64 w-64 rounded-full bg-emerald-300/10 blur-3xl" />

                <div className="relative flex flex-wrap items-end justify-between gap-4">
                  <div className="max-w-2xl">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-100/80">Individual component outputs</p>
                    <h3 className="mt-3 text-3xl font-semibold tracking-tight text-white">Module-wise analysis results</h3>
                    <p className="mt-3 text-sm leading-7 text-slate-300">
                      Each research component is displayed independently before the final combined investment insight is generated.
                    </p>
                  </div>
                  <div className="rounded-full border border-white/10 bg-slate-950/20 px-4 py-2 text-sm font-semibold text-white">
                    {componentOutputs.length} outputs
                  </div>
                </div>

                <div className="relative mt-8 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
                  <div className="rounded-[30px] border border-white/10 bg-slate-950/25 p-5">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-blue-100/55">Output flow</p>
                    <div className="mt-5 space-y-3">
                      {componentOutputs.map((output, index) => (
                        <div className="group relative rounded-[22px] border border-white/10 bg-white/7 p-4 transition hover:border-sky-200/25 hover:bg-white/10" key={output.title}>
                          {index < componentOutputs.length - 1 && <div className="absolute left-[34px] top-[58px] hidden h-6 w-px bg-white/15 sm:block" />}
                          <div className="flex items-center gap-4">
                            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-white/10 bg-slate-950/30 text-xs font-semibold text-white">
                              {output.code}
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-semibold text-white">{output.title}</p>
                              <p className="mt-1 truncate text-xs text-slate-400">{output.input}</p>
                            </div>
                            <span className={`shrink-0 rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${componentStatusStyles[output.tone]}`}>
                              {output.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="grid gap-5">
                    {componentOutputs.map((output) => (
                      <article className="relative overflow-hidden rounded-[30px] border border-white/10 bg-slate-950/25 p-6" key={output.title}>
                        <div className={`absolute inset-y-0 left-0 w-1.5 bg-gradient-to-b ${output.accent}`} />
                        <div className={`absolute -right-16 -top-16 h-40 w-40 rounded-full bg-gradient-to-br ${output.accent} blur-3xl`} />

                        <div className="relative flex flex-wrap items-start justify-between gap-4">
                          <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-blue-100/55">Module {output.code}</p>
                            <h4 className="mt-2 text-xl font-semibold text-white">{output.title}</h4>
                          </div>
                          <span className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${componentStatusStyles[output.tone]}`}>
                            {output.status}
                          </span>
                        </div>

                        <div className="relative mt-6 grid gap-5 md:grid-cols-[0.9fr_1.1fr] md:items-center">
                          <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-100/45">Output</p>
                            <p className="mt-3 text-2xl font-semibold leading-8 text-white">{output.output}</p>
                          </div>
                          <p className="rounded-[22px] border border-white/10 bg-white/7 p-4 text-sm leading-7 text-slate-300">
                            {output.evidence}
                          </p>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
                  {insightCards.map(([title, text]) => (
                    <div className="interactive-card rounded-[24px] border border-white/10 bg-white/8 p-5" key={title}>
                      <p className="text-sm font-semibold text-white">{title}</p>
                      <p className="mt-3 text-sm leading-7 text-slate-300">{text}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-[28px] border border-white/12 bg-white/10 p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-100/80">Generated preview</p>
                  <h3 className="mt-4 text-2xl font-semibold tracking-tight text-white">Decision support snapshot is ready.</h3>
                  <p className="mt-4 text-sm leading-7 text-slate-300">
                    {selectedStock?.companyName || "The selected company"} is ready for trend, volume, risk, and report-aware
                    interpretation using available CSE records.
                  </p>

                  <div className="mt-6 rounded-[22px] border border-white/10 bg-slate-950/30 p-5">
                    <div className="flex items-center justify-between gap-4">
                      <p className="text-sm font-semibold text-white">Insight confidence</p>
                      <p className="text-sm font-semibold text-emerald-100">82%</p>
                    </div>
                    <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/10">
                      <div className="h-full w-[82%] rounded-full bg-gradient-to-r from-emerald-300 to-sky-300" />
                    </div>
                  </div>

                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                      <p className="text-sm font-semibold text-white">Why it moved</p>
                      <p className="mt-2 text-sm leading-7 text-slate-300">
                        Market records, momentum behavior, and optional document context are combined into a plain-language explanation.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                      <p className="text-sm font-semibold text-white">Key contributing factors</p>
                      <div className="mt-3 grid gap-3">
                        {factorChips.map((factor) => (
                          <div className="rounded-2xl border border-white/10 bg-white/8 px-4 py-3 text-sm text-slate-200" key={factor}>
                            {factor}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default InsightPreviewPage;
