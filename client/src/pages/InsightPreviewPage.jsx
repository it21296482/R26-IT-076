import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import SiteHeader from "../components/SiteHeader";
import { useLanguage } from "../context/languageStore";
import api from "../lib/api";
import { INSIGHT_PREVIEW_STORAGE_KEY } from "../lib/analysisPreview";

const readStoredPreview = () => {
  try {
    return JSON.parse(sessionStorage.getItem(INSIGHT_PREVIEW_STORAGE_KEY));
  } catch {
    return null;
  }
};

const moneyText = (value) => (
  Number.isFinite(Number(value)) ? `LKR ${Number(value).toFixed(2)}` : "Not available"
);
const percentText = (value) => (
  Number.isFinite(Number(value)) ? `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(2)}%` : "Not available"
);

function ForecastPath({ market }) {
  const { t } = useLanguage();
  const available = (market?.horizons || []).filter((horizon) => horizon.estimated_close_lkr);
  if (!market || !available.length) return null;
  const series = [
    { key: "favourable", label: "Favourable range", color: "#34d399", dash: "8 7", field: "upper_80_lkr" },
    { key: "central", label: "Central path", color: "#67e8f9", dash: undefined, field: "estimated_close_lkr" },
    { key: "adverse", label: "Adverse range", color: "#fb7185", dash: "8 7", field: "lower_80_lkr" },
  ].map((item) => ({
    ...item,
    values: [market.current_price_lkr, ...available.map((horizon) => horizon[item.field])],
  }));
  const values = series.flatMap((item) => item.values);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = Math.max(max - min, Math.max(max * 0.015, 0.2));
  const pointsFor = (pathValues) => pathValues.map((value, index) => {
    const x = 70 + (index * 580) / Math.max(pathValues.length - 1, 1);
    const y = 178 - ((value - min) / spread) * 100;
    return { x, y, value, label: index === 0 ? "Now" : available[index - 1].label };
  });

  return (
    <div className="mt-6 overflow-hidden rounded-[26px] border border-white/10 bg-slate-950/25 p-4">
      <div className="flex flex-wrap justify-center gap-4 text-xs font-semibold text-slate-200">
        {series.map((item) => <span className="flex items-center gap-2" key={item.key}><i className="h-0.5 w-7 rounded-full" style={{ backgroundColor: item.color }} />{t(item.label)}</span>)}
      </div>
      <svg aria-label={t("Forecast path")} className="h-auto w-full" role="img" viewBox="0 0 720 230">
        {[80, 130, 180].map((y) => <line key={y} stroke="rgba(255,255,255,.08)" x1="45" x2="680" y1={y} y2={y} />)}
        {series.map((item) => {
          const points = pointsFor(item.values);
          return (
            <g key={item.key}>
              <polyline className="forecast-path-line" fill="none" points={points.map((point) => `${point.x},${point.y}`).join(" ")} stroke={item.color} strokeDasharray={item.dash} strokeLinecap="round" strokeLinejoin="round" strokeWidth={item.key === "central" ? 5 : 3} />
              {points.slice(1).map((point) => <circle cx={point.x} cy={point.y} fill="#0f172a" key={`${item.key}-${point.label}`} r={item.key === "central" ? 6 : 4} stroke={item.color} strokeWidth="3" />)}
            </g>
          );
        })}
        {pointsFor(series[1].values).map((point) => (
          <g key={point.label}>
            <text fill="#fff" fontSize="12" fontWeight="700" textAnchor="middle" x={point.x} y={point.y - 15}>{point.value.toFixed(2)}</text>
            <text fill="#94a3b8" fontSize="11" textAnchor="middle" x={point.x} y="210">{t(point.label)}</text>
          </g>
        ))}
      </svg>
      <p className="px-3 pb-2 text-center text-xs leading-5 text-slate-400">{t("Favourable and adverse lines show the measured 80% range, not guaranteed best or worst prices.")}</p>
    </div>
  );
}

function InsightPreviewPage({ analysisId: providedAnalysisId = "", embedded = false }) {
  const { t, language, locale } = useLanguage();
  const location = useLocation();
  const [previewRequest] = useState(
    providedAnalysisId ? { analysisId: providedAnalysisId } : (location.state || readStoredPreview())
  );
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const formatMoney = (value) => t(moneyText(value));
  const formatPercent = (value) => t(percentText(value));
  const formatDate = (value) => value && Number.isFinite(new Date(value).getTime())
    ? new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value))
    : t("Date unavailable");

  useEffect(() => {
    const controller = new AbortController();
    const loadAnalysis = async () => {
      if (!previewRequest?.analysisId) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError("");
      try {
        const { data } = await api.get(`/analysis/${previewRequest.analysisId}`, { params: { language }, signal: controller.signal });
        if (!controller.signal.aborted) setAnalysis(data.analysis);
      } catch (err) {
        if (!controller.signal.aborted) setError(err.response?.data?.message || "Unable to load this stock insight.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };

    loadAnalysis();
    return () => controller.abort();
  }, [language, previewRequest]);

  const market = analysis?.outputs?.market;
  const report = analysis?.outputs?.report;
  const legacyContext = analysis?.outputs?.externalContext;
  const newsContext = analysis?.outputs?.newsSentiment || legacyContext;
  const marketRiskContext = analysis?.outputs?.marketRiskContext || legacyContext;
  const risk = analysis?.outputs?.riskImpact;
  const unified = analysis?.outputs?.unifiedInsight?.insight;
  const priceScenarios = unified?.price_scenarios;
  const decisionBalance = unified?.decision_balance;
  const reportSummary = report?.status === "completed" ? report.insight?.investor_friendly_insight : null;
  const news = newsContext?.articles?.slice(0, 6) || [];
  const factors = marketRiskContext?.externalFactors?.factors || [];
  const deviationHistory = market?.deviation_history;
  const ContentWrapper = embedded ? "div" : "main";

  if (!previewRequest?.analysisId && !loading) {
    return (
      <div className="page-with-sticky-header min-h-screen pb-16">
        <SiteHeader compact />
        <main className="shell">
          <section className="surface-panel text-center">
            <p className="eyebrow !text-slate-500">{t("No analysis found")}</p>
            <h1 className="mt-4 text-4xl font-semibold text-slate-950">{t("Start with a stock and its report.")}</h1>
            <Link className="primary-cta mt-7" to="/dashboard">{t("Start analysis")}</Link>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className={embedded ? "scroll-mt-28" : "page-with-sticky-header min-h-screen pb-16"} id={embedded ? "stock-insight-result" : undefined}>
      {!embedded && <SiteHeader compact />}
      <ContentWrapper className={embedded ? "space-y-8" : "shell space-y-8"}>
        {loading && <section className="surface-panel text-center text-slate-600">{t("Loading your stock picture...")}</section>}
        {error && <section className="rounded-[26px] border border-rose-200 bg-rose-50 p-6 text-rose-700">{t(error)}</section>}

        {analysis && !loading && (
          <>
            {language !== "en" && (
              <p className={`rounded-2xl border p-4 text-sm leading-7 ${analysis.localization?.status === "completed" ? "border-sky-200 bg-sky-50 text-sky-900" : "border-amber-200 bg-amber-50 text-amber-900"}`} role="status">
                {t(analysis.localization?.status === "completed"
                  ? "Automatic translation. Check the original source before making financial decisions."
                  : "Some explanations could not be translated. Their original English text is shown; the analysis is unchanged.")}
              </p>
            )}
            <section className="market-hero relative overflow-hidden p-6 fade-rise md:p-10">
              <div className="market-orb absolute -right-20 -top-24 h-72 w-72 opacity-65" />
              <div className="relative z-10">
                <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
                  <div>
                    <p className="eyebrow !text-blue-100">{t("Your stock picture")}</p>
                    <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white md:text-6xl">{analysis.companyName}</h1>
                    <p className="mt-3 text-lg text-slate-300">{analysis.stockSymbol} · {t("Information checked")} {formatDate(analysis.createdAt)}</p>
                  </div>
                  <div className={`w-fit rounded-full border px-4 py-2 text-sm font-semibold ${analysis.status === "completed" ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100" : "border-amber-300/25 bg-amber-300/10 text-amber-100"}`}>
                    {analysis.status === "completed" ? t("Complete") : t("Ready with limitations")}
                  </div>
                </div>

                <div className="mt-8 rounded-[30px] border border-white/12 bg-white/10 p-6 md:p-8">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100">{t("In plain language")}</p>
                  <h2 className="mt-4 max-w-4xl text-3xl font-semibold leading-tight text-white">
                    {unified?.headline || t("Your combined stock explanation is being prepared.")}
                  </h2>
                  <p className="mt-5 max-w-4xl text-base leading-8 text-slate-300">
                    {unified?.plain_language_overview || t("The historical price, uploaded report, and current market context are being brought together.")}
                  </p>
                  {priceScenarios && (
                    <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      {[
                        [t("Current price"), priceScenarios.current_price_lkr, t("Where the stock is now")],
                        [t("Central path"), priceScenarios.central_path_lkr, priceScenarios.horizon],
                        [t("Favourable range"), priceScenarios.favourable_80_lkr, `${formatPercent(priceScenarios.favourable_change_pct)} ${t("scenario")}`],
                        [t("Adverse range"), priceScenarios.adverse_80_lkr, `${formatPercent(priceScenarios.adverse_change_pct)} ${t("scenario")}`],
                      ].map(([label, value, note]) => (
                        <div className="rounded-[20px] border border-white/12 bg-slate-950/30 p-4" key={label}>
                          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{t(label)}</p>
                          <p className="mt-2 text-2xl font-semibold text-white">{formatMoney(value)}</p>
                          <p className="mt-2 text-xs text-slate-400">{t(note)}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {risk && (
                    <div className="mt-5 rounded-[24px] border border-white/12 bg-slate-950/35 p-5">
                      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-100">{t("Combined market-risk reading")}</p>
                          <p className="mt-2 text-3xl font-semibold text-white">{t(risk.risk_level)}</p>
                        </div>
                        <p className="max-w-2xl text-sm leading-7 text-slate-300">{risk.plain_explanation}</p>
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-3">
                        {risk.top_drivers?.map((driver) => (
                          <div className="rounded-[18px] border border-white/10 bg-white/8 p-4" key={driver.label}>
                            <p className="text-sm font-semibold text-white">{t(driver.label)}</p>
                            <p className="mt-2 text-xs leading-5 text-slate-400">{driver.meaning}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {analysis.warnings?.length > 0 && (
                  <details className="mt-5 rounded-[22px] border border-amber-200/20 bg-amber-200/10 p-5 text-sm text-amber-50">
                    <summary className="cursor-pointer font-semibold">{t("What could not be fully verified")} ({analysis.warnings.length})</summary>
                    <div className="mt-4 grid gap-2 text-amber-50/80">
                      {analysis.warnings.map((warning) => <p key={warning}>{warning}</p>)}
                    </div>
                  </details>
                )}
              </div>
            </section>

            {decisionBalance && (
              <section className="grid gap-6 lg:grid-cols-2 fade-rise-delay-1">
                <div className="rounded-[26px] border border-sky-200 bg-sky-50 p-5 lg:col-span-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">{t("Overall evidence balance")}</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-950">{decisionBalance.label}</p>
                </div>
                <article className="rounded-[30px] border border-emerald-200 bg-emerald-50 p-6 md:p-8">
                  <p className="eyebrow !text-emerald-700">{t("What supports the potential")}</p>
                  <h2 className="mt-3 text-3xl font-semibold text-emerald-950">{t("Evidence working in the company's favour")}</h2>
                  <div className="mt-6 grid gap-3">
                    {decisionBalance.supporting_evidence?.slice(0, 6).map((item) => (
                      <p className="rounded-[18px] bg-white/80 p-4 text-sm leading-7 text-emerald-950" key={item}>{item}</p>
                    ))}
                  </div>
                </article>
                <article className="rounded-[30px] border border-rose-200 bg-rose-50 p-6 md:p-8">
                  <p className="eyebrow !text-rose-700">{t("What could go wrong")}</p>
                  <h2 className="mt-3 text-3xl font-semibold text-rose-950">{t("Evidence that increases downside risk")}</h2>
                  <div className="mt-6 grid gap-3">
                    {decisionBalance.risk_evidence?.slice(0, 6).map((item) => (
                      <p className="rounded-[18px] bg-white/80 p-4 text-sm leading-7 text-rose-950" key={item}>{item}</p>
                    ))}
                  </div>
                </article>
                <p className="rounded-[24px] border border-slate-200 bg-white p-5 text-sm leading-7 text-slate-700 lg:col-span-2">
                  {decisionBalance.plain_conclusion}
                </p>
              </section>
            )}

            <section className="surface-panel fade-rise-delay-1" id="component-market">
              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
                <div>
                  <p className="eyebrow !text-slate-500">{t("Potential price paths")}</p>
                  <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{t("What the recent pattern suggests")}</h2>
                </div>
                <div className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white">{t("Latest")}{" "}{formatMoney(market?.current_price_lkr)}
                </div>
              </div>

              {market ? (
                <>
                  <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {market.horizons.map((horizon) => (
                      <article className="rounded-[24px] border border-slate-200 bg-slate-50 p-5" key={horizon.key}>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{t(horizon.label)}</p>
                        {horizon.estimated_close_lkr ? (
                          <>
                            <p className="mt-4 text-3xl font-semibold text-slate-950">{formatMoney(horizon.estimated_close_lkr)}</p>
                            <p className={`mt-2 text-sm font-semibold ${horizon.change_from_latest_pct >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                              {formatPercent(horizon.change_from_latest_pct)}{" "}{t("from latest")}{" "}</p>
                            <div className="mt-4 grid gap-2 border-t border-slate-200 pt-4 text-xs">
                              <p className="flex justify-between gap-3 text-emerald-700"><span>{t("Favourable range")}</span><strong>{formatMoney(horizon.upper_80_lkr)} · {formatPercent(((horizon.upper_80_lkr / market.current_price_lkr) - 1) * 100)}</strong></p>
                              <p className="flex justify-between gap-3 text-slate-700"><span>{t("Central path")}</span><strong>{formatMoney(horizon.estimated_close_lkr)} · {formatPercent(horizon.change_from_latest_pct)}</strong></p>
                              <p className="flex justify-between gap-3 text-rose-700"><span>{t("Adverse range")}</span><strong>{formatMoney(horizon.lower_80_lkr)} · {formatPercent(((horizon.lower_80_lkr / market.current_price_lkr) - 1) * 100)}</strong></p>
                            </div>
                            <p className="mt-3 text-xs leading-5 text-slate-500">{t("Expected around")}{" "}{formatDate(horizon.target_date)} · {t(horizon.direction)}</p>
                            {horizon.status === "available_with_caution" && <p className="mt-3 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-800">{t("Treat cautiously: this estimate did not beat a simple unchanged-price comparison in its latest test.")}</p>}
                          </>
                        ) : (
                          <p className="mt-4 text-sm leading-7 text-slate-600">{horizon.message}</p>
                        )}
                      </article>
                    ))}
                  </div>
                  <div className="market-hero mt-6 p-4 md:p-6"><ForecastPath market={market} /></div>
                  {market.run_mode === "fresh_on_demand" && <p className="mt-4 text-center text-xs leading-5 text-slate-500">{t("Freshly calculated from {count} stored trading sessions through {date} · run {run}", { count: market.historical_row_count?.toLocaleString(locale), date: formatDate(market.as_of_date), run: market.run_id?.slice(0, 8) })}</p>}
                </>
              ) : <p className="mt-6 text-slate-600">{t("A supported market estimate was not available for this stock.")}</p>}
            </section>

            <section className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
              <article className="surface-panel" id="component-market-check">
                <p className="eyebrow !text-slate-500">{t("Unusual movement check")}</p>
                <h2 className="mt-3 text-3xl font-semibold text-slate-950">{market?.anomaly?.detected ? t("An unusual deviation was detected") : t("No unusual deviation at the latest check")}</h2>
                {market?.anomaly ? (
                  <>
                    <div className="mt-6 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-[20px] bg-slate-950 p-4 text-white"><p className="text-xs text-slate-400">{t("Actual price")}</p><p className="mt-2 text-xl font-semibold">{formatMoney(market.anomaly.actual_price_lkr)}</p></div>
                      <div className="rounded-[20px] bg-slate-100 p-4"><p className="text-xs text-slate-500">{t("Expected price")}</p><p className="mt-2 text-xl font-semibold text-slate-950">{formatMoney(market.anomaly.expected_price_lkr)}</p></div>
                      <div className="rounded-[20px] bg-slate-100 p-4"><p className="text-xs text-slate-500">{t("Deviation")}</p><p className="mt-2 text-xl font-semibold text-slate-950">{formatMoney(market.anomaly.signed_deviation_lkr)}</p></div>
                      <div className="rounded-[20px] bg-slate-100 p-4"><p className="text-xs text-slate-500">{t("Anomaly score / threshold")}</p><p className="mt-2 text-xl font-semibold text-slate-950">{market.anomaly.liquidity_aware_score} / {market.anomaly.threshold}</p></div>
                    </div>
                    <p className="mt-6 text-sm leading-7 text-slate-600">{String(market.anomaly.explanation || "").replace(/the model's/gi, "the expected").replace(/model/gi, "analysis")}</p>
                    {deviationHistory?.observations > 0 && (
                      <div className="mt-6 border-t border-slate-200 pt-6">
                        <div className="flex flex-wrap items-end justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-slate-950">{t("Recent deviation history")}</p>
                            <p className="mt-1 text-xs leading-5 text-slate-500">
                              {t("{count} unusual sessions across {total} recent trading sessions", { count: deviationHistory.detected_count, total: deviationHistory.observations })}
                            </p>
                          </div>
                          <p className="text-xs text-slate-500">{formatDate(deviationHistory.window_start)}{" "}{t("to")}{" "}{formatDate(deviationHistory.window_end)}</p>
                        </div>
                        <div className="mt-4 grid gap-3">
                          {(deviationHistory.detected_events || []).slice(-4).reverse().map((event) => (
                            <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-4" key={event.date}>
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="font-semibold text-slate-950">{formatDate(event.date)}</p>
                                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${event.signed_deviation_lkr < 0 ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"}`}>
                                  {event.deviation_pct >= 0 ? "+" : ""}{Number(event.deviation_pct).toFixed(1)}% {t("vs expected")}
                                </span>
                              </div>
                              <p className="mt-2 text-sm leading-6 text-slate-600">{t("Actual")} {formatMoney(event.actual_price_lkr)} · {t("expected")} {formatMoney(event.expected_price_lkr)} · {t("score")} {event.anomaly_score} / {event.threshold}
                              </p>
                            </div>
                          ))}
                        </div>
                        <p className="mt-4 text-xs leading-5 text-slate-500">{t("External events from the same dates are useful context, but timing overlap alone does not prove what caused the movement.")}</p>
                      </div>
                    )}
                  </>
                ) : <p className="mt-5 text-slate-600">{t("This check was unavailable.")}</p>}
              </article>

              <article className="surface-panel" id="component-report">
                <p className="eyebrow !text-slate-500">{t("What the company report says")}</p>
                <h2 className="mt-3 text-3xl font-semibold text-slate-950">{reportSummary ? t("Verified report takeaways") : t("Report evidence needs review")}</h2>
                {reportSummary ? (
                  <>
                    <p className="mt-5 text-base leading-8 text-slate-600">{reportSummary.summary}</p>
                    <div className="mt-6 grid gap-5 sm:grid-cols-2">
                      <div className="rounded-[22px] border border-emerald-100 bg-emerald-50 p-5"><p className="font-semibold text-emerald-950">{t("Strengths in the report")}</p>{reportSummary.key_strengths?.map((item) => <p className="mt-3 text-sm leading-6 text-emerald-900" key={item}>• {item}</p>)}</div>
                      <div className="rounded-[22px] border border-amber-100 bg-amber-50 p-5"><p className="font-semibold text-amber-950">{t("Concerns in the report")}</p>{reportSummary.key_concerns?.map((item) => <p className="mt-3 text-sm leading-6 text-amber-900" key={item}>• {item}</p>)}</div>
                    </div>
                    <p className="mt-5 text-xs text-slate-500">{t("{count} page-level source quotes verified.", { count: report.evidence_validation?.valid_count || 0 })}</p>
                  </>
                ) : (
                  <p className="mt-5 text-base leading-8 text-slate-600">{t("The report was received, but its important claims did not yet have enough verifiable page evidence. It is not used as a confirmed company conclusion.")}</p>
                )}
              </article>
            </section>

            <section className="surface-panel" id="component-news">
              <p className="eyebrow !text-slate-500">{t("News sentiment and external-market risk")}</p>
              <h2 className="mt-3 text-3xl font-semibold text-slate-950">{t("Relevant events and wider risk conditions")}</h2>
              <p className="mt-4 max-w-3xl text-base leading-8 text-slate-600">{t("News sentiment identifies relevant events. External-market indicators provide separate risk context. Neither proves that an event or indicator caused the stock price to move.")}</p>

              <div className="mt-7 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
                <div className="grid gap-3">
                  {news.length ? news.map((article) => (
                    <a className="interactive-card rounded-[22px] border border-slate-200 bg-slate-50 p-5" href={article.url} key={`${article.title}-${article.publishedAt}`} rel="noreferrer" target="_blank">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><span>{article.source}</span><span>{formatDate(article.publishedAt)}</span></div>
                      <h3 className="mt-3 font-semibold leading-6 text-slate-950">{article.title}</h3>
                      <p className="mt-2 text-xs capitalize text-slate-500">{t(article.scope)} {t("context")} · {t(article.sentiment.label)} {t("wording")}</p>
                    </a>
                  )) : <p className="rounded-[22px] bg-slate-50 p-5 text-slate-600">{t("No dated relevant articles were collected during this run.")}</p>}
                </div>

                <div className="grid content-start gap-3" id="component-risk">
                  {factors.map((factor) => (
                    <article className="rounded-[22px] bg-slate-950 p-5 text-white" key={factor.key}>
                      <div className="flex items-start justify-between gap-4">
                        <div><h3 className="font-semibold">{t(factor.label)}</h3><p className="mt-1 text-xs text-slate-500">{t(factor.unit)}</p></div>
                        <span className="text-right text-sm text-slate-300">{factor.latestValue}<br />{t("30 days")} {formatPercent(factor.change30dPct)}</span>
                      </div>
                      <p className="mt-4 text-sm leading-7 text-slate-200">{factor.meaning?.businessChannel}</p>
                      <p className="mt-3 text-xs leading-6 text-slate-400"><strong className="text-slate-200">{t("If it rises:")}</strong> {factor.meaning?.ifFactorRises}</p>
                      <p className="mt-2 text-xs leading-6 text-slate-400"><strong className="text-slate-200">{t("If it falls:")}</strong> {factor.meaning?.ifFactorFalls}</p>
                      <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                        <p className="rounded-xl bg-white/8 p-3 text-slate-300">{t("90-day move")}<strong className="mt-1 block text-white">{formatPercent(factor.change90dPct)}</strong></p>
                        <p className="rounded-xl bg-white/8 p-3 text-slate-300">{t("Movement explained")}<strong className="mt-1 block text-white">{Number(factor.explanatorySharePct || 0).toFixed(1)}%</strong></p>
                      </div>
                      <p className="mt-4 text-xs leading-6 text-cyan-100">{factor.meaning?.contributionEstimate || factor.interpretation}</p>
                      <p className="mt-3 text-xs text-slate-500">{t("Compared across {count} shared trading days. Association does not prove cause.", { count: factor.overlappingReturnDays })}</p>
                    </article>
                  ))}
                </div>
              </div>
            </section>

            {unified && (
              <section className="market-hero p-6 md:p-9">
                <div className="grid gap-6 lg:grid-cols-3">
                  <div><p className="eyebrow !text-blue-100">{t("Potential")}</p>{unified.potential?.map((item) => <p className="mt-4 text-sm leading-7 text-slate-200" key={item}>{item}</p>)}</div>
                  <div><p className="eyebrow !text-blue-100">{t("Key risks")}</p>{unified.key_risks?.map((item) => <p className="mt-4 text-sm leading-7 text-slate-200" key={item}>{item}</p>)}</div>
                  <div><p className="eyebrow !text-blue-100">{t("What could change the picture")}</p>{unified.what_could_change_the_picture?.map((item) => <p className="mt-4 text-sm leading-7 text-slate-200" key={item}>{item}</p>)}</div>
                </div>
                <div className="mt-8 border-t border-white/10 pt-6"><p className="text-sm leading-7 text-slate-300">{unified.uncertainty}</p><p className="mt-4 font-semibold text-amber-200">{unified.non_advisory_note}</p></div>
              </section>
            )}

            <div className="flex justify-center">
              {embedded
                ? <a className="secondary-cta" href="#analysis-workspace">{t("Analyze another stock")}</a>
                : <Link className="secondary-cta" to="/dashboard">{t("Analyze another stock")}</Link>}
            </div>
          </>
        )}
      </ContentWrapper>
    </div>
  );
}

export default InsightPreviewPage;
