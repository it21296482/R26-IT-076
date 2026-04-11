import { useEffect, useRef, useState } from "react";
import SiteHeader from "../components/SiteHeader";
import { useAuth } from "../hooks/useAuth";
import api from "../lib/api";

const previewCards = [
  {
    title: "Trend chart",
    text: "Highlights meaningful direction changes instead of exposing noisy raw data.",
  },
  {
    title: "Anomaly highlight",
    text: "Flags unusual market behavior that deserves investor attention.",
  },
  {
    title: "Explanation panel",
    text: "Explains what likely influenced the change in plain language.",
  },
  {
    title: "Risk indicator",
    text: "Summarizes confidence and uncertainty clearly for decision support.",
  },
];

function UserDashboardPage() {
  const { user } = useAuth();
  const formRef = useRef(null);
  const [stockUniverse, setStockUniverse] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [workspaceReady, setWorkspaceReady] = useState(false);

  useEffect(() => {
    const fetchUniverse = async () => {
      try {
        const { data } = await api.get("/stocks/universe");
        setStockUniverse(data.stocks);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to load stock records.");
      } finally {
        setLoading(false);
      }
    };

    fetchUniverse();
  }, []);

  const selectedStock = stockUniverse.find((stock) => stock.symbol === selectedSymbol);

  const handlePrepareWorkspace = (event) => {
    event.preventDefault();

    if (!selectedSymbol) {
      setError("Please select a stock.");
      return;
    }

    setError("");
    setWorkspaceReady(true);
  };

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader compact />

      <main className="shell space-y-10">
        <section className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-6 fade-rise">
            <p className="eyebrow">Welcome back</p>
            <h1 className="max-w-4xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
              A clearer path to understanding the market, {user?.name}.
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-slate-300">
              Select a stock, optionally upload a report, and let the system turn complex financial inputs into clear
              decision-support insights.
            </p>
            <button className="primary-cta" onClick={() => formRef.current?.scrollIntoView({ behavior: "smooth" })} type="button">
              Start Analysis
            </button>
          </div>

          <div className="dark-card chart-grid relative overflow-hidden p-6 fade-rise-delay-1">
            <div className="trend-path absolute left-6 right-6 top-12 h-28 bg-gradient-to-r from-emerald-300/90 via-sky-300/90 to-amber-300/85" />
            <div className="relative z-10 space-y-4">
              <img alt="Investor insight workspace" className="h-56 w-full rounded-[24px] object-cover" src="/assets/Blogs_Paytm_Bond-Market-vs.-Stock-Market_-Whats-the-Difference_-1.jpg" />
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/6 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-400">What you get</p>
                  <p className="mt-2 text-sm leading-7 text-slate-200">Insights first, raw complexity second.</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/6 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Why it matters</p>
                  <p className="mt-2 text-sm leading-7 text-slate-200">Clearer understanding leads to better decisions.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-[0.92fr_1.08fr]" ref={formRef}>
          <div className="light-card p-8 fade-rise">
            <div className="space-y-4">
              <p className="eyebrow !text-slate-500">Start analysis</p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-900">Simple flow, clear direction</h2>
              <p className="text-base leading-8 text-slate-600">
                Choose a listed company, upload the latest report if available, and move into a guided insight view.
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
                <span className="text-sm font-medium text-slate-700">Upload report (optional)</span>
                <input
                  className="input-surface file:mr-4 file:rounded-full file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                  type="file"
                />
              </label>

              {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
              {loading && <p className="text-sm text-slate-500">Loading available stocks...</p>}
              {selectedFile && <p className="text-sm text-slate-500">Attached report: {selectedFile.name}</p>}

              {selectedStock && (
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Listing</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{selectedStock.symbol}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Rows</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{selectedStock.recordCount}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Latest date</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{new Date(selectedStock.latestTradeDate).toLocaleDateString()}</p>
                  </div>
                </div>
              )}

              <button className="primary-cta w-full" disabled={!stockUniverse.length} type="submit">
                View Insights
              </button>
            </form>
          </div>

          <div className="dark-card chart-grid relative overflow-hidden p-8 fade-rise-delay-1">
            <div className="trend-path absolute left-6 right-6 top-16 h-28 bg-gradient-to-r from-emerald-300/90 via-sky-300/90 to-amber-300/85" />
            <div className="relative z-10 space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                {previewCards.map((card) => (
                  <div className="rounded-[24px] border border-white/10 bg-white/6 p-5" key={card.title}>
                    <p className="text-sm font-semibold text-white">{card.title}</p>
                    <p className="mt-3 text-sm leading-7 text-slate-300">{card.text}</p>
                  </div>
                ))}
              </div>

              {workspaceReady && (
                <div className="rounded-[24px] border border-emerald-300/18 bg-emerald-300/10 p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-200">Insight preview</p>
                  <div className="mt-4 grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
                    <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                      <p className="text-sm font-semibold text-white">Trend summary</p>
                      <p className="mt-2 text-sm leading-7 text-slate-300">
                        The selected stock is showing a meaningful shift in direction, and the platform will highlight
                        what changed in clear language.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                      <p className="text-sm font-semibold text-white">Risk signal</p>
                      <p className="mt-2 text-sm leading-7 text-slate-300">Short-term uncertainty elevated</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default UserDashboardPage;
