import { useEffect, useRef, useState } from "react";
import SiteHeader from "../components/SiteHeader";
import { useAuth } from "../hooks/useAuth";
import api from "../lib/api";

const insightCards = [
  ["Trend signal", "Positive momentum pattern ready for analysis."],
  ["Anomaly check", "Volume and price behavior scanned for unusual movement."],
  ["Sentiment pulse", "Market context prepared for news and event interpretation."],
  ["Risk indicator", "Confidence and uncertainty summarized for decision support."],
];

const factorChips = ["Price momentum", "Report context", "Sentiment signal"];

function UserDashboardPage() {
  const { user } = useAuth();
  const formRef = useRef(null);
  const [stockUniverse, setStockUniverse] = useState([]);
  const [recentReports, setRecentReports] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [uploadingReport, setUploadingReport] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [workspaceReady, setWorkspaceReady] = useState(false);

  useEffect(() => {
    const loadWorkspace = async () => {
      try {
        // Load both market options and report-intake history so the dashboard reflects the full analysis setup state.
        const [{ data: stockData }, { data: reportData }] = await Promise.all([api.get("/stocks/universe"), api.get("/reports")]);
        setStockUniverse(stockData.stocks);
        setRecentReports(reportData.reports);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to load the investor workspace.");
      } finally {
        setLoading(false);
        setReportsLoading(false);
      }
    };

    loadWorkspace();
  }, []);

  const selectedStock = stockUniverse.find((stock) => stock.symbol === selectedSymbol);
  const latestReport = recentReports[0] || null;
  const pipelineStatus = [
    ["Stock data", selectedStock ? "Ready" : "Waiting"],
    ["Report intake", latestReport?.processingStatus || (selectedFile ? "Selected" : "Optional")],
    ["Sentiment", workspaceReady ? "Queued" : "Pending"],
    ["XAI insight", workspaceReady ? "Preparing" : "Waiting"],
  ];

  const refreshReports = async () => {
    const { data } = await api.get("/reports");
    setRecentReports(data.reports);
  };

  const handlePrepareWorkspace = async (event) => {
    event.preventDefault();

    if (!selectedSymbol || !selectedStock) {
      setError("Please select a stock.");
      return;
    }

    setError("");
    setSuccess("");

    if (selectedFile) {
      setUploadingReport(true);

      try {
        // Send the selected company plus PDF together so the backend can create a report intake record for this analysis.
        const formData = new FormData();
        formData.append("symbol", selectedStock.symbol);
        formData.append("companyName", selectedStock.companyName);
        formData.append("file", selectedFile);

        const { data } = await api.post("/reports/upload", formData);
        setSuccess(data.message);
        await refreshReports();
        setSelectedFile(null);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to upload the financial report.");
        setUploadingReport(false);
        return;
      }

      setUploadingReport(false);
    } else {
      setSuccess("Workspace prepared with stock data only. You can attach a financial report later for richer document insights.");
    }

    setWorkspaceReady(true);
  };

  const formatBytes = (sizeBytes) => {
    if (!sizeBytes) {
      return "0 KB";
    }

    const sizeInMb = sizeBytes / (1024 * 1024);

    if (sizeInMb >= 1) {
      return `${sizeInMb.toFixed(1)} MB`;
    }

    return `${Math.max(1, Math.round(sizeBytes / 1024))} KB`;
  };

  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader compact />

      <main className="shell space-y-8">
        <section className="surface-panel fade-rise">
          <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <div className="space-y-6">
              <p className="eyebrow">Investor workspace</p>
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
                Investor insight console for CSE market decisions.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-600">
                Welcome {user?.name}. Build one focused analysis by selecting a CSE-listed company, adding report context,
                and reviewing explainable signals before making a decision.
              </p>
              <div className="flex flex-wrap gap-3">
                <button className="primary-cta" onClick={() => formRef.current?.scrollIntoView({ behavior: "smooth" })} type="button">
                  Start Analysis
                </button>
                <div className="rounded-full border border-[#dbe7fb] bg-[#f8fbff] px-5 py-3 text-sm font-semibold text-slate-600">
                  {stockUniverse.length} companies available
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="metric-card p-5">
                <p className="eyebrow !text-slate-500">Selected stock</p>
                <p className="mt-5 text-3xl font-semibold text-slate-950">{selectedSymbol || "Pending"}</p>
                <p className="mt-3 text-sm leading-6 text-slate-500">
                  Choose a company to activate trend, anomaly, and explanation preview panels.
                </p>
              </div>
              <div className="metric-card p-5">
                <p className="eyebrow !text-slate-500">Analysis mode</p>
                <p className="mt-5 text-3xl font-semibold text-slate-950">{workspaceReady ? "Ready" : "Setup"}</p>
                <p className="mt-3 text-sm leading-6 text-slate-500">
                  {workspaceReady ? "Preview generated with current inputs." : "Inputs are waiting for review."}
                </p>
              </div>
              <div className="metric-card p-5 sm:col-span-2">
                <p className="eyebrow !text-slate-500">Workspace focus</p>
                <p className="mt-4 text-base leading-7 text-slate-600">
                  Turn raw market records, optional report evidence, and sentiment cues into a single decision-support view.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-8 xl:grid-cols-[390px_1fr]" ref={formRef}>
          <aside className="surface-panel fade-rise xl:sticky xl:top-32 xl:self-start">
            <div className="space-y-4">
              <p className="eyebrow !text-slate-500">Analysis controls</p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Prepare insight preview</h2>
              <p className="text-base leading-8 text-slate-600">
                Choose a company and optionally attach the latest financial report to enrich the generated explanation.
              </p>
            </div>

            <form className="mt-8 space-y-5" onSubmit={handlePrepareWorkspace}>
              <label className="block space-y-2">
                <span className="text-sm font-medium text-slate-700">Select stock</span>
                <select className="input-surface" onChange={(event) => setSelectedSymbol(event.target.value)} value={selectedSymbol}>
                  <option value="">Choose a listed company</option>
                  {stockUniverse.map((stock) => (
                    <option key={stock.symbol} value={stock.symbol}>
                      {stock.companyName} ({stock.symbol})
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-slate-700">Upload financial report (optional)</span>
                <input
                  accept=".pdf,application/pdf"
                  className="input-surface file:mr-4 file:rounded-full file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                  type="file"
                />
              </label>

              {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
              {success && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}
              {loading && <p className="text-sm text-slate-500">Loading available stocks...</p>}
              {selectedFile && <p className="text-sm text-slate-500">Attached report: {selectedFile.name}</p>}

              <div className="rounded-[24px] border border-[#dbe7fb] bg-[#f8fbff] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Input summary</p>
                <div className="mt-4 grid gap-3">
                  <div className="flex items-center justify-between gap-4 rounded-2xl bg-white px-4 py-3 text-sm">
                    <span className="text-slate-500">Company</span>
                    <span className="font-semibold text-slate-900">{selectedStock?.symbol || "Not selected"}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 rounded-2xl bg-white px-4 py-3 text-sm">
                    <span className="text-slate-500">Report</span>
                    <span className="max-w-36 truncate font-semibold text-slate-900">{selectedFile?.name || "Optional"}</span>
                  </div>
                </div>
              </div>

              <button className="primary-cta w-full" disabled={!stockUniverse.length || uploadingReport} type="submit">
                {uploadingReport ? "Uploading report..." : "Generate Insight Preview"}
              </button>
            </form>
          </aside>

          <section className="market-hero relative overflow-hidden p-6 fade-rise-delay-1 md:p-8">
            <div className="market-orb absolute -right-16 bottom-0 h-44 w-44 opacity-75" />
            <div className="relative z-10 space-y-6">
              <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr] lg:items-stretch">
                <div className="rounded-[28px] border border-white/10 bg-white/8 p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="eyebrow !text-blue-100">Live insight board</p>
                      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">
                        {selectedStock?.companyName || "Select a company to begin"}
                      </h2>
                    </div>
                    <div className="rounded-full border border-white/10 bg-emerald-300/15 px-4 py-2 text-sm font-semibold text-emerald-100">
                      {workspaceReady ? "Confidence 82%" : "Preview mode"}
                    </div>
                  </div>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {selectedStock && (
                      <>
                        <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                          <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Ticker</p>
                          <p className="mt-2 text-lg font-semibold text-white">{selectedStock.symbol}</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                          <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Records</p>
                          <p className="mt-2 text-lg font-semibold text-white">{selectedStock.recordCount}</p>
                        </div>
                      </>
                    )}
                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Risk watch</p>
                      <p className="mt-2 text-lg font-semibold text-white">{workspaceReady ? "Moderate" : "Pending"}</p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Report context</p>
                      <p className="mt-2 text-lg font-semibold text-white">
                        {latestReport?.processingStatus || (selectedFile ? "Selected" : "Optional")}
                      </p>
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
                  <h3 className="mt-4 text-2xl font-semibold tracking-tight text-white">
                    {workspaceReady ? "Decision support snapshot is ready." : "Your preview will appear here."}
                  </h3>
                  <p className="mt-4 text-sm leading-7 text-slate-300">
                    {workspaceReady
                      ? `${selectedStock?.companyName || "The selected company"} is ready for trend, volume, risk, and report-aware interpretation using available CSE records.`
                      : "Select a stock and generate the preview to see trend movement, uncertainty, contributing factors, and explanation notes in one place."}
                  </p>

                  <div className="mt-6 rounded-[22px] border border-white/10 bg-slate-950/30 p-5">
                    <div className="flex items-center justify-between gap-4">
                      <p className="text-sm font-semibold text-white">Insight confidence</p>
                      <p className="text-sm font-semibold text-emerald-100">{workspaceReady ? "82%" : "34%"}</p>
                    </div>
                    <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/10">
                      <div className={`h-full rounded-full bg-gradient-to-r from-emerald-300 to-sky-300 ${workspaceReady ? "w-[82%]" : "w-[34%]"}`} />
                    </div>
                  </div>

                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                      <p className="text-sm font-semibold text-white">Why it moved</p>
                      <p className="mt-2 text-sm leading-7 text-slate-300">
                        {workspaceReady
                          ? "Market records, momentum behavior, and optional document context are combined into a plain-language explanation."
                          : "Waiting for analysis input."}
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

              <div className="rounded-[28px] border border-white/12 bg-white/8 p-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-100/80">Financial report intake</p>
                    <h3 className="mt-3 text-2xl font-semibold tracking-tight text-white">Recent document uploads</h3>
                  </div>
                  <div className="rounded-full border border-white/10 bg-slate-950/20 px-4 py-2 text-sm font-semibold text-white">
                    {recentReports.length} tracked
                  </div>
                </div>

                <div className="mt-6 space-y-4">
                  {reportsLoading && <p className="text-sm text-slate-300">Loading recent uploads...</p>}

                  {!reportsLoading && !recentReports.length && (
                    <div className="rounded-2xl border border-dashed border-white/15 bg-slate-950/20 px-5 py-4 text-sm leading-7 text-slate-300">
                      No financial reports uploaded yet. Attach a CSE company report to start your document-understanding pipeline.
                    </div>
                  )}

                  {/* This queue gives the user a visible audit trail for the first stage of the research pipeline. */}
                  {recentReports.map((report) => (
                    <div className="rounded-[24px] border border-white/10 bg-slate-950/25 p-5" key={report._id}>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-lg font-semibold text-white">{report.companyName}</p>
                          <p className="mt-1 text-sm text-slate-300">
                            {report.stockSymbol} • {report.originalFilename}
                          </p>
                        </div>
                        <div className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">
                          {report.processingStatus}
                        </div>
                      </div>

                      <div className="mt-4 grid gap-3 sm:grid-cols-3">
                        <div className="rounded-2xl border border-white/10 bg-white/8 px-4 py-3">
                          <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Uploaded</p>
                          <p className="mt-2 text-sm font-semibold text-white">{new Date(report.uploadedAt).toLocaleString()}</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/8 px-4 py-3">
                          <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">File size</p>
                          <p className="mt-2 text-sm font-semibold text-white">{formatBytes(report.sizeBytes)}</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/8 px-4 py-3">
                          <p className="text-[10px] uppercase tracking-[0.2em] text-blue-100/60">Pipeline note</p>
                          <p className="mt-2 text-sm font-semibold text-white">{report.summary || "Awaiting processing"}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}

export default UserDashboardPage;
