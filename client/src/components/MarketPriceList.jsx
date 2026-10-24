import { useEffect, useState } from "react";
import api from "../lib/api";
import { useLanguage } from "../context/languageStore";
import { priceChangeClass } from "../lib/priceChange";

export default function MarketPriceList({ supportedSymbols, refreshKey }) {
  const { t, locale } = useLanguage();
  const [snapshot, setSnapshot] = useState(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api.get("/stocks/prices", { signal: controller.signal }).then(({ data }) => {
      if (!controller.signal.aborted) { setSnapshot(data); setPage(0); }
    }).catch(() => {
      if (!controller.signal.aborted) setError("CSE prices are temporarily unavailable. Try refreshing the price list.");
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [refresh, refreshKey]);
  const filtered = (snapshot?.stocks || []).filter((s) => `${s.symbol} ${s.companyName}`.toLowerCase().includes(query.toLowerCase()));
  const rows = filtered.slice(page * 15, page * 15 + 15);
  return (
    <section className="surface-panel" aria-label={t("CSE market prices")}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><p className="eyebrow !text-slate-500">{t("CSE market prices")}</p>
          <h2 className="mt-3 text-2xl font-semibold text-slate-950">{t("Latest reported stock prices")}</h2>
        </div>
        <button className="secondary-cta" type="button" disabled={loading} onClick={() => { setLoading(true); setError(""); setRefresh((v) => v + 1); }}>{t("Refresh prices")}</button>
      </div>
      <p className="mt-4 text-sm leading-7 text-slate-600">{t("Prices show the last trade reported by CSE, not guaranteed real-time quotes. Full analysis is available only for stocks with supported history and research coverage.")}</p>
      {snapshot && <p className="mt-2 text-xs text-slate-500">{t("{count} securities returned by CSE", { count: snapshot.stocks.length })} · {new Date(snapshot.fetchedAt).toLocaleString(locale)}</p>}
      {error && <p role="alert" className="mt-4 text-sm text-amber-800">{t(error)}</p>}
      {loading && <p className="mt-4 text-sm text-slate-500">{t("Refreshing prices...")}</p>}
      <details className="mt-5">
        <summary className="cursor-pointer font-semibold text-blue-800">{t("Browse CSE prices")}</summary>
        <input className="input-surface mt-4" aria-label={t("Search company or symbol")} placeholder={t("Search company or symbol")} value={query} onChange={(e) => { setQuery(e.target.value); setPage(0); }} />
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500"><tr><th className="p-3">{t("Stock")}</th><th className="p-3">{t("Price (LKR)")}</th><th className="p-3">{t("Change (%)")}</th><th className="p-3">{t("Last trade")}</th></tr></thead>
            <tbody>{rows.map((s) => <tr className="border-b border-slate-100" key={s.symbol}>
              <td className="p-3"><strong>{s.companyName}</strong><p className="text-xs text-slate-500">{s.symbol}{supportedSymbols.includes(s.symbol) ? ` · ${t("Analysis supported")}` : ""}</p></td>
              <td className="whitespace-nowrap p-3">{s.price === null ? t("Not available") : s.price.toFixed(2)}</td>
              <td className={`p-3 ${priceChangeClass(s.changePercent)}`}>{s.changePercent === null ? t("Not available") : `${s.changePercent > 0 ? "+" : ""}${s.changePercent.toFixed(2)}`}</td>
              <td className="whitespace-nowrap p-3">{s.lastTradeDate ? new Date(s.lastTradeDate).toLocaleDateString(locale) : t("Date unavailable")}</td>
            </tr>)}</tbody>
          </table>
        </div>
        <div className="mt-4 flex items-center justify-between gap-4">
          <button type="button" className="secondary-cta" disabled={page === 0} onClick={() => setPage(page - 1)}>{t("Previous")}</button>
          <span className="text-sm text-slate-500">{t("Page {page} of {total}", { page: page + 1, total: Math.max(1, Math.ceil(filtered.length / 15)) })}</span>
          <button type="button" className="secondary-cta" disabled={(page + 1) * 15 >= filtered.length} onClick={() => setPage(page + 1)}>{t("Next")}</button>
        </div>
      </details>
    </section>
  );
}
