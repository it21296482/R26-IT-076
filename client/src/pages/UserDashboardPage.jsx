import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";
import { useAuth } from "../hooks/useAuth";
import api from "../lib/api";

const INSIGHT_PREVIEW_STORAGE_KEY = "cseInsightPreview";

function UserDashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stockUniverse, setStockUniverse] = useState([]);
  const [recentReports, setRecentReports] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploadingReport, setUploadingReport] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const loadWorkspace = async () => {
      try {
        const [{ data: stockData }, { data: reportData }] = await Promise.all([api.get("/stocks/universe"), api.get("/reports")]);
        setStockUniverse(stockData.stocks);
        setRecentReports(reportData.reports);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to load the investor workspace.");
      } finally {
        setLoading(false);
      }
    };

    loadWorkspace();
  }, []);

  const selectedStock = stockUniverse.find((stock) => stock.symbol === selectedSymbol);
  const latestReport = recentReports.find((report) => report.stockSymbol === selectedSymbol) || null;

  const openInsightPreview = (report) => {
    const previewPayload = {
      generatedAt: new Date().toISOString(),
      reportId: report?._id || latestReport?._id || null,
      selectedSymbol: selectedStock.symbol,
    };

    sessionStorage.setItem(INSIGHT_PREVIEW_STORAGE_KEY, JSON.stringify(previewPayload));
    navigate("/dashboard/insight-preview", { state: previewPayload });
  };

  const refreshReports = async () => {
    const { data } = await api.get("/reports");
    setRecentReports(data.reports);
    return data.reports;
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
        const formData = new FormData();
        formData.append("symbol", selectedStock.symbol);
        formData.append("companyName", selectedStock.companyName);
        formData.append("file", selectedFile);

        const { data } = await api.post("/reports/upload", formData);
        setSuccess(data.message);
        await refreshReports();
        setSelectedFile(null);
        openInsightPreview(data.report);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to upload the financial report.");
      } finally {
        setUploadingReport(false);
      }

      return;
    }

    setSuccess("Analysis started with stock data only. Opening the visualization dashboard...");
    openInsightPreview(latestReport);
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
                Prepare your CSE insight preview.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-600">
                Welcome {user?.name}. Select a CSE-listed company and optionally attach a financial report. After the
                analysis starts, the module outputs open in a dedicated visualization dashboard.
              </p>
            </div>

            <div className="metric-card overflow-hidden p-3">
              <img
                alt="CSE stock chart analysis"
                className="h-72 w-full rounded-[22px] object-cover md:h-80"
                src="/assets/rTh56Sw5YjFvpW8SF5pJvV.jpg"
              />
            </div>
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-2">
          <div className="surface-panel relative overflow-hidden p-8 fade-rise-delay-1">
            <div className="absolute -right-20 -top-20 h-56 w-56 rounded-full bg-[#dfeaff] opacity-80 blur-2xl" />
            <div className="relative z-10">
              <p className="eyebrow">Analysis overview</p>
              <h3 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight text-slate-950">
                From input setup to module visualization.
              </h3>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600">
                This page is focused only on collecting the analysis inputs. Once started, the system redirects to a
                separate dashboard that visualizes every component output clearly.
              </p>

              <div className="mt-8 grid gap-4">
                <div className="rounded-[24px] border border-[#dbe7fb] bg-[#f8fbff] p-5">
                  <p className="text-sm font-semibold text-slate-950">1. Select company</p>
                  <p className="mt-3 text-sm leading-7 text-slate-600">
                    Choose the CSE stock that will be used for market-data analysis.
                  </p>
                </div>
                <div className="rounded-[24px] border border-[#dbe7fb] bg-[#f8fbff] p-5">
                  <p className="text-sm font-semibold text-slate-950">2. Add report</p>
                  <p className="mt-3 text-sm leading-7 text-slate-600">
                    Attach a PDF report when document evidence is required.
                  </p>
                </div>
                <div className="rounded-[24px] border border-[#dbe7fb] bg-[#f8fbff] p-5">
                  <p className="text-sm font-semibold text-slate-950">3. View dashboard</p>
                  <p className="mt-3 text-sm leading-7 text-slate-600">
                    Open stock, report, sentiment, risk, and XAI outputs as visual modules.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <aside className="surface-panel fade-rise">
            <div className="space-y-4">
              <p className="eyebrow !text-slate-500">Analysis controls</p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Prepare insight preview</h2>
              <p className="text-base leading-8 text-slate-600">
                Choose a company and optionally attach the latest financial report. The analysis output will open as a
                module-wise visualization dashboard.
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
                    <span className="max-w-36 truncate font-semibold text-slate-900">
                      {selectedFile?.name || latestReport?.originalFilename || "Optional"}
                    </span>
                  </div>
                </div>
              </div>

              <button className="primary-cta w-full" disabled={!stockUniverse.length || uploadingReport} type="submit">
                {uploadingReport ? "Uploading report..." : "Start Analysis"}
              </button>
            </form>
          </aside>
        </section>
      </main>

      <footer className="mt-14">
        <section className="footer-shell">
          <div className="shell py-5">
            <div className="text-center text-sm text-white/65">
              Copyright © 2026 CSE Insight Generator. All rights reserved. Terms & Conditions.
            </div>
          </div>
        </section>
      </footer>
    </div>
  );
}

export { INSIGHT_PREVIEW_STORAGE_KEY };
export default UserDashboardPage;
