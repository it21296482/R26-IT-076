import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";
import api from "../lib/api";
import { INSIGHT_PREVIEW_STORAGE_KEY } from "./UserDashboardPage";

const readStoredPreview = () => {
  try {
    return JSON.parse(sessionStorage.getItem(INSIGHT_PREVIEW_STORAGE_KEY));
  } catch {
    return null;
  }
};

const formatMoney = (value) => (
  Number.isFinite(Number(value)) ? `LKR ${Number(value).toFixed(2)}` : "Not available"
);
const formatPercent = (value) => (
  Number.isFinite(Number(value)) ? `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(2)}%` : "Not available"
);
const formatDate = (value) => (
  value ? new Intl.DateTimeFormat("en-LK", { dateStyle: "medium" }).format(new Date(value)) : "Date unavailable"
);

function ForecastPath({ market }) {
  const available = (market?.horizons || []).filter((horizon) => horizon.estimated_close_lkr);
  if (!market || !available.length) return null;
  const values = [market.current_price_lkr, ...available.map((horizon) => horizon.estimated_close_lkr)];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = Math.max(max - min, Math.max(max * 0.015, 0.2));
  const points = values.map((value, index) => {
    const x = 70 + (index * 580) / Math.max(values.length - 1, 1);
    const y = 178 - ((value - min) / spread) * 100;
    return { x, y, value, label: index === 0 ? "Now" : available[index - 1].label };
  });

  return (
    <div className="mt-6 overflow-hidden rounded-[26px] border border-white/10 bg-slate-950/25 p-4">
      <svg aria-label="Forecast path" className="h-auto w-full" role="img" viewBox="0 0 720 230">
        <defs>
          <linearGradient id="forecastLine" x1="0" x2="1">
            <stop offset="0%" stopColor="#67e8f9" />
            <stop offset="100%" stopColor="#fbbf24" />
          </linearGradient>
        </defs>
        {[80, 130, 180].map((y) => <line key={y} stroke="rgba(255,255,255,.08)" x1="45" x2="680" y1={y} y2={y} />)}
        <polyline fill="none" points={points.map((point) => `${point.x},${point.y}`).join(" ")} stroke="url(#forecastLine)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" />
        {points.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} fill="#0f172a" r="7" stroke="#a5f3fc" strokeWidth="4" />
            <text fill="#fff" fontSize="12" fontWeight="700" textAnchor="middle" x={point.x} y={point.y - 17}>{point.value.toFixed(2)}</text>
            <text fill="#94a3b8" fontSize="11" textAnchor="middle" x={point.x} y="210">{point.label}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function InsightPreviewPage() {
  const location = useLocation();
  const [previewRequest] = useState(location.state || readStoredPreview());
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadAnalysis = async () => {
      if (!previewRequest?.analysisId) {
        setLoading(false);
        return;
      }
      try {
        const { data } = await api.get(`/analysis/${previewRequest.analysisId}`);
        setAnalysis(data.analysis);
      } catch (err) {
        setError(err.response?.data?.message || "Unable to load this stock insight.");
      } finally {
        setLoading(false);
      }
    };

    loadAnalysis();
  }, [previewRequest]);

  const market = analysis?.outputs?.market;
  const report = analysis?.outputs?.report;
  const context = analysis?.outputs?.externalContext;
  const unified = analysis?.outputs?.unifiedInsight?.insight;
  const reportSummary = report?.status === "completed" ? report.insight?.investor_friendly_insight : null;
  const news = context?.articles?.slice(0, 6) || [];
  const factors = context?.externalFactors?.factors || [];
  const deviationHistory = market?.deviation_history;

  if (!previewRequest?.analysisId && !loading) {
    return (
      <div className="page-with-sticky-header min-h-screen pb-16">
        <SiteHeader compact />
        <main className="shell">
          <section className="surface-panel text-center">
            <p className="eyebrow !text-slate-500">No analysis found</p>
            <h1 className="mt-4 text-4xl font-semibold text-slate-950">Start with a stock and its report.</h1>
            <Link className="primary-cta mt-7" to="/dashboard">Start analysis</Link>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="page-with-sticky-header min-h-screen pb-16">
      <SiteHeader compact />
      <main className="shell space-y-8">
        {loading && <section className="surface-panel text-center text-slate-600">Loading your stock picture...</section>}
        {error && <section className="rounded-[26px] border border-rose-200 bg-rose-50 p-6 text-rose-700">{error}</section>}

        {analysis && !loading && (
          <>
            <section className="market-hero relative overflow-hidden p-6 fade-rise md:p-10">
              <div className="market-orb absolute -right-20 -top-24 h-72 w-72 opacity-65" />
              <div className="relative z-10">
                <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
                  <div>
                    <p className="eyebrow !text-blue-100">Your stock picture</p>
                    <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white md:text-6xl">{analysis.companyName}</h1>
                    <p className="mt-3 text-lg text-slate-300">{analysis.stockSymbol} · Information checked {formatDate(analysis.createdAt)}</p>
                  </div>
                  <div className={`w-fit rounded-full border px-4 py-2 text-sm font-semibold ${analysis.status === "completed" ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100" : "border-amber-300/25 bg-amber-300/10 text-amber-100"}`}>
                    {analysis.status === "completed" ? "Complete" : "Ready with limitations"}
                  </div>
                </div>

                <div className="mt-8 rounded-[30px] border border-white/12 bg-white/10 p-6 md:p-8">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100">In plain language</p>
                  <h2 className="mt-4 max-w-4xl text-3xl font-semibold leading-tight text-white">
                    {unified?.headline || "Your combined stock explanation is being prepared."}
                  </h2>
                  <p className="mt-5 max-w-4xl text-base leading-8 text-slate-300">
                    {unified?.plain_language_overview || "The historical price, uploaded report, and current market context are being brought together."}
                  </p>
                </div>

                {analysis.warnings?.length > 0 && (
                  <details className="mt-5 rounded-[22px] border border-amber-200/20 bg-amber-200/10 p-5 text-sm text-amber-50">
                    <summary className="cursor-pointer font-semibold">What could not be fully verified ({analysis.warnings.length})</summary>
                    <div className="mt-4 grid gap-2 text-amber-50/80">
                      {analysis.warnings.map((warning) => <p key={warning}>{warning}</p>)}
                    </div>
                  </details>
                )}
              </div>
            </section>

            <section className="surface-panel fade-rise-delay-1">
              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
                <div>
                  <p className="eyebrow !text-slate-500">Potential price paths</p>
                  <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">What the recent pattern suggests</h2>
                </div>
                <div className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white">
                  Latest {formatMoney(market?.current_price_lkr)}
                </div>
              </div>

              {market ? (
                <>
                  <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {market.horizons.map((horizon) => (
                      <article className="rounded-[24px] border border-slate-200 bg-slate-50 p-5" key={horizon.key}>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{horizon.label}</p>
                        {horizon.estimated_close_lkr ? (
                          <>
                            <p className="mt-4 text-3xl font-semibold text-slate-950">{formatMoney(horizon.estimated_close_lkr)}</p>
                            <p className={`mt-2 text-sm font-semibold ${horizon.change_from_latest_pct >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                              {formatPercent(horizon.change_from_latest_pct)} from latest
                            </p>
                            <p className="mt-3 text-xs leading-5 text-slate-500">Expected around {formatDate(horizon.target_date)} · {horizon.direction}</p>
                            {horizon.status === "available_with_caution" && <p className="mt-3 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-800">Treat cautiously: the advanced estimate did not beat a simple benchmark in its latest test.</p>}
                          </>
                        ) : (
                          <p className="mt-4 text-sm leading-7 text-slate-600">{horizon.message}</p>
                        )}
                      </article>
                    ))}
                  </div>
                  <div className="market-hero mt-6 p-4 md:p-6"><ForecastPath market={market} /></div>
                </>
              ) : <p className="mt-6 text-slate-600">A supported market estimate was not available for this stock.</p>}
            </section>

            <section className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
              <article className="surface-panel">
                <p className="eyebrow !text-slate-500">Unusual movement check</p>
                <h2 className="mt-3 text-3xl font-semibold text-slate-950">{market?.anomaly?.detected ? "An unusual deviation was detected" : "No unusual deviation at the latest check"}</h2>
                {market?.anomaly ? (
                  <>
                    <div className="mt-6 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-[20px] bg-slate-950 p-4 text-white"><p className="text-xs text-slate-400">Actual price</p><p className="mt-2 text-xl font-semibold">{formatMoney(market.anomaly.actual_price_lkr)}</p></div>
                      <div className="rounded-[20px] bg-slate-100 p-4"><p className="text-xs text-slate-500">Expected price</p><p className="mt-2 text-xl font-semibold text-slate-950">{formatMoney(market.anomaly.expected_price_lkr)}</p></div>
                      <div className="rounded-[20px] bg-slate-100 p-4"><p className="text-xs text-slate-500">Deviation</p><p className="mt-2 text-xl font-semibold text-slate-950">{formatMoney(market.anomaly.signed_deviation_lkr)}</p></div>
                      <div className="rounded-[20px] bg-slate-100 p-4"><p className="text-xs text-slate-500">Anomaly score / threshold</p><p className="mt-2 text-xl font-semibold text-slate-950">{market.anomaly.liquidity_aware_score} / {market.anomaly.threshold}</p></div>
                    </div>
                    <p className="mt-6 text-sm leading-7 text-slate-600">{String(market.anomaly.explanation || "").replace(/the model's/gi, "the expected").replace(/model/gi, "analysis")}</p>
                    {deviationHistory?.observations > 0 && (
                      <div className="mt-6 border-t border-slate-200 pt-6">
                        <div className="flex flex-wrap items-end justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-slate-950">Recent deviation history</p>
                            <p className="mt-1 text-xs leading-5 text-slate-500">
                              {deviationHistory.detected_count} unusual {deviationHistory.detected_count === 1 ? "session" : "sessions"} across {deviationHistory.observations} recent trading sessions
                            </p>
                          </div>
                          <p className="text-xs text-slate-500">{formatDate(deviationHistory.window_start)} to {formatDate(deviationHistory.window_end)}</p>
                        </div>
                        <div className="mt-4 grid gap-3">
                          {(deviationHistory.detected_events || []).slice(-4).reverse().map((event) => (
                            <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-4" key={event.date}>
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="font-semibold text-slate-950">{formatDate(event.date)}</p>
                                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${event.signed_deviation_lkr < 0 ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"}`}>
                                  {event.deviation_pct >= 0 ? "+" : ""}{Number(event.deviation_pct).toFixed(1)}% vs expected
                                </span>
                              </div>
                              <p className="mt-2 text-sm leading-6 text-slate-600">
                                Actual {formatMoney(event.actual_price_lkr)} · expected {formatMoney(event.expected_price_lkr)} · score {event.anomaly_score} / {event.threshold}
                              </p>
                            </div>
                          ))}
                        </div>
                        <p className="mt-4 text-xs leading-5 text-slate-500">External events from the same dates are useful context, but timing overlap alone does not prove what caused the movement.</p>
                      </div>
                    )}
                  </>
                ) : <p className="mt-5 text-slate-600">This check was unavailable.</p>}
              </article>

              <article className="surface-panel">
                <p className="eyebrow !text-slate-500">What the company report says</p>
                <h2 className="mt-3 text-3xl font-semibold text-slate-950">{reportSummary ? "Verified report takeaways" : "Report evidence needs review"}</h2>
                {reportSummary ? (
                  <>
                    <p className="mt-5 text-base leading-8 text-slate-600">{reportSummary.summary}</p>
                    <div className="mt-6 grid gap-5 sm:grid-cols-2">
                      <div className="rounded-[22px] border border-emerald-100 bg-emerald-50 p-5"><p className="font-semibold text-emerald-950">Strengths in the report</p>{reportSummary.key_strengths?.map((item) => <p className="mt-3 text-sm leading-6 text-emerald-900" key={item}>• {item}</p>)}</div>
                      <div className="rounded-[22px] border border-amber-100 bg-amber-50 p-5"><p className="font-semibold text-amber-950">Concerns in the report</p>{reportSummary.key_concerns?.map((item) => <p className="mt-3 text-sm leading-6 text-amber-900" key={item}>• {item}</p>)}</div>
                    </div>
                    <p className="mt-5 text-xs text-slate-500">{report.evidence_validation?.valid_count || 0} page-level source quotes verified.</p>
                  </>
                ) : (
                  <p className="mt-5 text-base leading-8 text-slate-600">The report was received, but its important claims did not yet have enough verifiable page evidence. It is not used as a confirmed company conclusion.</p>
                )}
              </article>
            </section>

            <section className="surface-panel">
              <p className="eyebrow !text-slate-500">What is happening around the stock</p>
              <h2 className="mt-3 text-3xl font-semibold text-slate-950">Relevant events and wider market context</h2>
              <p className="mt-4 max-w-3xl text-base leading-8 text-slate-600">News and global-market relationships add context. They do not prove that an event caused the stock price to move.</p>

              <div className="mt-7 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
                <div className="grid gap-3">
                  {news.length ? news.map((article) => (
                    <a className="interactive-card rounded-[22px] border border-slate-200 bg-slate-50 p-5" href={article.url} key={`${article.title}-${article.publishedAt}`} rel="noreferrer" target="_blank">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><span>{article.source}</span><span>{formatDate(article.publishedAt)}</span></div>
                      <h3 className="mt-3 font-semibold leading-6 text-slate-950">{article.title}</h3>
                      <p className="mt-2 text-xs capitalize text-slate-500">{article.scope} context · {article.sentiment.label} wording</p>
                    </a>
                  )) : <p className="rounded-[22px] bg-slate-50 p-5 text-slate-600">No dated relevant articles were collected during this run.</p>}
                </div>

                <div className="grid content-start gap-3">
                  {factors.map((factor) => (
                    <article className="rounded-[22px] bg-slate-950 p-5 text-white" key={factor.key}>
                      <div className="flex items-center justify-between gap-4"><h3 className="font-semibold">{factor.label}</h3><span className="text-sm text-slate-300">30d {formatPercent(factor.change30dPct)}</span></div>
                      <p className="mt-3 text-sm leading-7 text-slate-300">{factor.interpretation}</p>
                      <p className="mt-3 text-xs text-slate-500">{factor.overlappingReturnDays} overlapping market days</p>
                    </article>
                  ))}
                </div>
              </div>
            </section>

            {unified && (
              <section className="market-hero p-6 md:p-9">
                <div className="grid gap-6 lg:grid-cols-3">
                  <div><p className="eyebrow !text-blue-100">Potential</p>{unified.potential?.map((item) => <p className="mt-4 text-sm leading-7 text-slate-200" key={item}>{item}</p>)}</div>
                  <div><p className="eyebrow !text-blue-100">Key risks</p>{unified.key_risks?.map((item) => <p className="mt-4 text-sm leading-7 text-slate-200" key={item}>{item}</p>)}</div>
                  <div><p className="eyebrow !text-blue-100">What could change the picture</p>{unified.what_could_change_the_picture?.map((item) => <p className="mt-4 text-sm leading-7 text-slate-200" key={item}>{item}</p>)}</div>
                </div>
                <div className="mt-8 border-t border-white/10 pt-6"><p className="text-sm leading-7 text-slate-300">{unified.uncertainty}</p><p className="mt-4 font-semibold text-amber-200">{unified.non_advisory_note}</p></div>
              </section>
            )}

            <div className="flex justify-center"><Link className="secondary-cta" to="/dashboard">Analyze another stock</Link></div>
          </>
        )}
      </main>
    </div>
  );
}

export default InsightPreviewPage;
