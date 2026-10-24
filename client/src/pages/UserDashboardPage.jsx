import { useLanguage } from "../context/languageStore";
import { useEffect, useState } from "react";
import SiteHeader from "../components/SiteHeader";
import { useAuth } from "../hooks/useAuth";
import api from "../lib/api";
import { INSIGHT_PREVIEW_STORAGE_KEY } from "../lib/analysisPreview";
import InsightPreviewPage from "./InsightPreviewPage";
import MarketPriceList from "../components/MarketPriceList";
import { progressUrl } from "../lib/analysisProgress";
import AnalysisProgress from "../components/AnalysisProgress";

const MAX_REPORT_SIZE = 10 * 1024 * 1024;
function UserDashboardPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [stockUniverse, setStockUniverse] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [analysisId, setAnalysisId] = useState("");
  const [progress, setProgress] = useState(null);
  const [progressRequestId, setProgressRequestId] = useState("");
  const [progressDisconnected, setProgressDisconnected] = useState(false);
  const [pricesRefreshKey, setPricesRefreshKey] = useState(0);
  const [directoryWarning, setDirectoryWarning] = useState("");

  useEffect(() => {
    if (!progressRequestId) return;
    const stream = new EventSource(progressUrl(api.defaults.baseURL, progressRequestId, window.location.origin), { withCredentials: true });
    stream.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data);
        if (!Number.isFinite(update.percent) || update.percent < 0 || update.percent > 100) return;
        setProgress((current) => ["completed", "partial", "failed"].includes(current?.status)
          ? current : ({ ...update, percent: Math.max(current?.percent || 0, update.percent) }));
        setProgressDisconnected(false);
      } catch { /* A malformed progress message must not interrupt analysis. */ }
    };
    stream.onerror = () => setProgressDisconnected(true);
    return () => stream.close();
  }, [progressRequestId]);

  useEffect(() => {
    const loadStocks = async () => {
      try {
        const { data } = await api.get("/stocks/universe");
        setStockUniverse(data.stocks || []);
        setDirectoryWarning(data.warning || "");
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
    if (!selectedStock.analysisEligible) {
      setError("This security could not be confirmed in the current CSE directory. Please refresh and try again.");
      return;
    }
    if (!selectedFile) {
      setError("Upload the latest quarterly or annual financial report for the selected company.");
      return;
    }

    setAnalyzing(true);
    setAnalysisId("");
    setProgress({ stage: "upload", percent: 0, status: "processing" });
    setProgressDisconnected(false);
    setError("");
    try {
      const formData = new FormData();
      formData.append("symbol", selectedStock.symbol);
      formData.append("companyName", selectedStock.companyName);
      formData.append("file", selectedFile);

      const { data: uploadData } = await api.post("/reports/upload", formData);
      const clientRequestId = crypto.randomUUID();
      setProgressRequestId(clientRequestId);
      const { data: analysisData } = await api.post("/analysis", {
        stockSymbol: selectedStock.symbol,
        reportId: uploadData.report._id,
        clientRequestId,
      });
      setProgress({ percent: 100, stage: analysisData.analysis.status === "completed" ? "completed" : "partial",
        status: analysisData.analysis.status === "completed" ? "completed" : "partial" });
      setPricesRefreshKey((key) => key + 1);
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
      setProgress((current) => ({ ...current, stage: "failed", status: "failed" }));
      setError(err.response?.data?.message || "The analysis could not be completed. Please try again.");
    } finally {
      setProgressRequestId("");
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
              <p className="eyebrow !text-blue-100">{t("Your analysis workspace")}</p>
              <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white md:text-6xl">{t("See the complete picture behind a CSE stock.")}{" "}</h1>
              <p className="max-w-xl text-base leading-8 text-slate-300 md:text-lg">
                {t("Welcome {name}. Choose a company and attach its latest financial report. We will bring market behaviour, company information, relevant events, and market risk into one clear explanation.", { name: user?.name || "" })}
              </p>

              <div className="grid gap-3 sm:grid-cols-3">
                {[t("Select a stock"), t("Upload its report"), t("Understand the result")].map((step, index) => (
                  <div className="rounded-[22px] border border-white/10 bg-white/8 p-4" key={step}>
                    <p className="text-xs font-semibold text-sky-200">0{index + 1}</p>
                    <p className="mt-2 text-sm font-semibold text-white">{t(step)}</p>
                  </div>
                ))}
              </div>
            </div>

            <form className="rounded-[32px] border border-white/12 bg-white/95 p-6 shadow-[0_30px_90px_rgba(2,8,23,0.3)] md:p-8" onSubmit={handleAnalyze}>
              <div>
                <p className="eyebrow !text-slate-500">{t("Start a new analysis")}</p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{t("Two inputs. One clear view.")}</h2>
                <p className="mt-3 text-sm leading-7 text-slate-600">{t("The report must belong to the company you select. PDF files up to 10 MB are supported.")}{" "}</p>
              </div>

              <div className="mt-7 space-y-5">
                <label className="block space-y-2">
                  <span className="text-sm font-semibold text-slate-800">{t("Stock")}</span>
                  <select
                    className="input-surface"
                    disabled={loading || analyzing}
                    onChange={(event) => setSelectedSymbol(event.target.value)}
                    required
                    value={selectedSymbol}
                  >
                    <option value="">{t("Select a listed company")}</option>
                    {[
                      { label: t("Analysis supported"), stocks: stockUniverse.filter((stock) => stock.analysisAvailable) },
                      { label: t("Prepare history when analyzing"), stocks: stockUniverse.filter((stock) => !stock.analysisAvailable) },
                    ].filter((group) => group.stocks.length).map((group) => (
                      <optgroup label={group.label} key={group.label}>
                        {group.stocks.map((stock) => (
                          <option key={stock.symbol} value={stock.symbol} disabled={!stock.analysisEligible}>
                            {stock.companyName} ({stock.symbol})
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                  <span className="block text-xs leading-5 text-slate-500">{t("All CSE listings can be selected. Analysis checks real history and trains stock-specific models when enough evidence is available. Missing evidence is clearly shown.")}</span>
                  {directoryWarning && <span className="block text-xs leading-5 text-amber-800">{t(directoryWarning)}</span>}
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-semibold text-slate-800">{t("Latest financial report")}</span>
                  <span className="input-surface flex cursor-pointer items-center gap-3 focus-within:ring-2 focus-within:ring-blue-400">
                    <input
                      accept=".pdf,application/pdf"
                      aria-label={t("Latest financial report")}
                      className="sr-only"
                      disabled={analyzing}
                      onChange={handleFileChange}
                      required
                      type="file"
                    />
                    <span className="shrink-0 rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white">{t("Choose PDF")}</span>
                    <span className="min-w-0 truncate text-sm text-slate-500">{selectedFile?.name || t("No file selected")}</span>
                  </span>
                  <span className="block text-xs leading-5 text-slate-500">{t("Quarterly or annual company report in PDF format.")}</span>
                </label>
              </div>

              {selectedStock && selectedFile && (
                <div className="mt-5 rounded-[22px] border border-sky-100 bg-sky-50 p-4 text-sm text-slate-700">
                  <p className="font-semibold text-slate-950">{t("Ready to analyze {symbol}", { symbol: selectedStock.symbol })}</p>
                  <p className="mt-1 truncate">{selectedFile.name}</p>
                </div>
              )}
              {error && <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{t(error)}</div>}
              {loading && <p className="mt-5 text-sm text-slate-500">{t("Loading available stocks...")}</p>}

              <button
                className="primary-cta mt-6 w-full"
                disabled={loading || analyzing || !selectedStock?.analysisEligible}
                type="submit"
              >
                {analyzing ? t("Refreshing prices and building your stock picture...") : t("Analyze with latest prices")}
              </button>
              {analyzing && (
                <p className="mt-4 text-center text-xs leading-5 text-slate-500">{t("Reading the report and checking current context can take a few minutes. Keep this page open.")}{" "}</p>
              )}
              <AnalysisProgress progress={progress} analyzing={analyzing} progressDisconnected={progressDisconnected} />
            </form>
          </div>
        </section>

        <MarketPriceList key={pricesRefreshKey} supportedSymbols={stockUniverse.filter((stock) => stock.analysisAvailable).map((stock) => stock.symbol)} refreshKey={pricesRefreshKey} />

        {analysisId && (
          <div id="stock-insight-result" className="scroll-mt-28">
            <InsightPreviewPage key={analysisId} analysisId={analysisId} embedded />
          </div>
        )}
      </main>
    </div>
  );
}

export default UserDashboardPage;
