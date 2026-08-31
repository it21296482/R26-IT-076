import { useEffect, useState } from "react";
import SiteHeader from "../components/SiteHeader";
import { useAuth } from "../hooks/useAuth";
import api from "../lib/api";
import { INSIGHT_PREVIEW_STORAGE_KEY } from "../lib/analysisPreview";
import InsightPreviewPage from "./InsightPreviewPage";

const MAX_REPORT_SIZE = 10 * 1024 * 1024;

function UserDashboardPage() {
  const { user } = useAuth();
  const [stockUniverse, setStockUniverse] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [analysisId, setAnalysisId] = useState("");

  useEffect(() => {
    const loadStocks = async () => {
      try {
        const { data } = await api.get("/stocks/universe");
        setStockUniverse(data.stocks || []);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to load the available stocks.");
      } finally {
        setLoading(false);
      }
    };

    loadStocks();
  }, []);

  const selectedStock = stockUniverse.find((stock) => stock.symbol === selectedSymbol);

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setError("");
    if (file && file.size > MAX_REPORT_SIZE) {
      event.target.value = "";
      setSelectedFile(null);
      setError("The PDF must be 10 MB or smaller.");
      return;
    }
    setSelectedFile(file);
  };

  const handleAnalyze = async (event) => {
    event.preventDefault();
    if (!selectedStock) {
      setError("Select a stock before starting the analysis.");
      return;
    }
    if (!selectedFile) {
      setError("Upload the latest quarterly or annual financial report for the selected company.");
      return;
    }

    setAnalyzing(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("symbol", selectedStock.symbol);
      formData.append("companyName", selectedStock.companyName);
      formData.append("file", selectedFile);

      const { data: uploadData } = await api.post("/reports/upload", formData);
      const { data: analysisData } = await api.post("/analysis", {
        stockSymbol: selectedStock.symbol,
        reportId: uploadData.report._id,
      });
      const previewPayload = {
        analysisId: analysisData.analysis._id,
        selectedSymbol: selectedStock.symbol,
      };
      sessionStorage.setItem(INSIGHT_PREVIEW_STORAGE_KEY, JSON.stringify(previewPayload));
      setAnalysisId(analysisData.analysis._id);
      window.setTimeout(() => {
        document.getElementById("stock-insight-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } catch (err) {
      setError(err.response?.data?.message || "The analysis could not be completed. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader compact />

      <main className="shell space-y-10">
        <section className="market-hero relative overflow-hidden p-6 fade-rise md:p-10 lg:p-12" id="analysis-workspace">
          <div className="market-orb absolute -right-20 -top-24 h-72 w-72 opacity-70" />
          <div className="relative z-10 grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div className="space-y-6">
              <p className="eyebrow !text-blue-100">Your analysis workspace</p>
              <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
                See the complete picture behind a CSE stock.
              </h1>
              <p className="max-w-xl text-base leading-8 text-slate-300 md:text-lg">
                Welcome {user?.name}. Choose a company and attach its latest financial report. We will bring market
                behaviour, company information, relevant events, and market risk into one clear explanation.
              </p>

              <div className="grid gap-3 sm:grid-cols-3">
                {["Select a stock", "Upload its report", "Understand the result"].map((step, index) => (
                  <div className="rounded-[22px] border border-white/10 bg-white/8 p-4" key={step}>
                    <p className="text-xs font-semibold text-sky-200">0{index + 1}</p>
                    <p className="mt-2 text-sm font-semibold text-white">{step}</p>
                  </div>
                ))}
              </div>
            </div>

            <form className="rounded-[32px] border border-white/12 bg-white/95 p-6 shadow-[0_30px_90px_rgba(2,8,23,0.3)] md:p-8" onSubmit={handleAnalyze}>
              <div>
                <p className="eyebrow !text-slate-500">Start a new analysis</p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Two inputs. One clear view.</h2>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  The report must belong to the company you select. PDF files up to 10 MB are supported.
                </p>
              </div>

              <div className="mt-7 space-y-5">
                <label className="block space-y-2">
                  <span className="text-sm font-semibold text-slate-800">Stock</span>
                  <select
                    className="input-surface"
                    disabled={loading || analyzing}
                    onChange={(event) => setSelectedSymbol(event.target.value)}
                    required
                    value={selectedSymbol}
                  >
                    <option value="">Select a listed company</option>
                    {stockUniverse.map((stock) => (
                      <option key={stock.symbol} value={stock.symbol}>
                        {stock.companyName} ({stock.symbol})
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-semibold text-slate-800">Latest financial report</span>
                  <input
                    accept=".pdf,application/pdf"
                    className="input-surface file:mr-4 file:rounded-full file:border-0 file:bg-slate-950 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white"
                    disabled={analyzing}
                    onChange={handleFileChange}
                    required
                    type="file"
                  />
                  <span className="block text-xs leading-5 text-slate-500">Quarterly or annual company report in PDF format.</span>
                </label>
              </div>

              {selectedStock && selectedFile && (
                <div className="mt-5 rounded-[22px] border border-sky-100 bg-sky-50 p-4 text-sm text-slate-700">
                  <p className="font-semibold text-slate-950">Ready to analyze {selectedStock.symbol}</p>
                  <p className="mt-1 truncate">{selectedFile.name}</p>
                </div>
              )}
              {error && <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
              {loading && <p className="mt-5 text-sm text-slate-500">Loading available stocks...</p>}

              <button
                className="primary-cta mt-6 w-full"
                disabled={loading || analyzing || !stockUniverse.length}
                type="submit"
              >
                {analyzing ? "Refreshing prices and building your stock picture..." : "Analyze with latest prices"}
              </button>
              {analyzing && (
                <p className="mt-4 text-center text-xs leading-5 text-slate-500">
                  Reading the report and checking current context can take a few minutes. Keep this page open.
                </p>
              )}
              <p className="mt-3 text-center text-xs leading-5 text-slate-500">
                Analyze refreshes currently supported prices from the official CSE trade summary before the research stages run.
              </p>
            </form>
          </div>
        </section>

        {analysisId && (
          <InsightPreviewPage key={analysisId} analysisId={analysisId} embedded />
        )}
      </main>
    </div>
  );
}

export default UserDashboardPage;
