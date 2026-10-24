"""Cross-stock aggregation for the multi-stock Component 1 evaluation.

    python experiments/aggregate_results.py [--out artifacts/paper_v2]

Reads <out>/per_stock/<CODE>/*.csv and writes <out>/aggregate/:
  inclusion.csv                  listing -> exported -> eligible -> evaluated counts
  agg_daily_detection.csv        Exp A, per detector, development vs held-out stocks
  agg_episode_detection.csv      Exp B, detection rate, delay, false alarms
  agg_pattern_enrichment.csv     Exp D, label rate in episodes vs out-of-episode windows
  agg_paired_tests.csv           Wilcoxon signed-rank tests across stocks (Holm-adjusted)
  agg_model_selection.csv        how often validation chose persistence (w = 0)
  tables_generated.tex           LaTeX tables ready for the paper
Development stocks (rules designed on them) are reported separately from held-out stocks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DEV = {"JKH", "BIL", "JKH_N0000", "BIL_N0000"}
PROPOSED_A = "Proposed: score OR band (past-only adaptive)"
PROPOSED_B = "Daily: proposed score OR band"


def load(per_stock: Path, name: str) -> pd.DataFrame:
    frames = []
    for d in sorted(per_stock.iterdir()):
        f = d / name
        if f.exists():
            x = pd.read_csv(f)
            x["stock"] = d.name
            frames.append(x)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def cohort(stock: str) -> str:
    return "development" if stock in DEV else "held-out"


def holm(p: list[float]) -> list[float]:
    order = np.argsort(p)
    adj = np.empty(len(p))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def wilcoxon(x: pd.Series, y: pd.Series) -> tuple[int, float, float, float]:
    d = (x - y).dropna()
    d = d[d != 0]
    if len(d) < 6:
        return len(d), float("nan"), float("nan"), float("nan")
    res = stats.wilcoxon(d, zero_method="wilcox", alternative="two-sided", method="auto")
    # matched-pairs rank-biserial correlation
    ranks = stats.rankdata(np.abs(d))
    r = (ranks[d > 0].sum() - ranks[d < 0].sum()) / ranks.sum()
    return len(d), float(res.statistic), float(res.pvalue), float(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "paper_v2"))
    ap.add_argument("--manifest", default=str(ROOT / "data" / "actuals_all" / "export_manifest.json"))
    args = ap.parse_args()
    out = Path(args.out)
    per = out / "per_stock"
    agg = out / "aggregate"
    agg.mkdir(parents=True, exist_ok=True)

    # ---------------- inclusion flow
    logs = [pd.read_csv(p) for p in sorted(out.glob("run_log*.csv"))]
    log = pd.concat(logs).drop_duplicates("stock", keep="last") if logs else pd.DataFrame(columns=["stock", "status"])
    inc = {"listings": np.nan, "exported": np.nan}
    if Path(args.manifest).exists():
        m = json.loads(Path(args.manifest).read_text())
        inc["listings"] = m.get("listings")
        inc["exported"] = sum(r["status"] == "exported" for r in m["results"])
    inc["eligible"] = int((log["status"] != "excluded").sum())
    inc["evaluated"] = int((log["status"] == "done").sum())
    inc["failed"] = int((log["status"] == "failed").sum())
    excl = log[log["status"] == "excluded"]["reason"].str.extract(r"^(only|history starts|history ends|traded)")[0].value_counts().to_dict() if "reason" in log else {}
    pd.DataFrame([{**inc, **{f"excluded_{k.replace(' ', '_')}": v for k, v in excl.items()}}]).to_csv(agg / "inclusion.csv", index=False)

    tests = []
    tex = []

    # ---------------- Exp A: daily detection
    a = load(per, "exp_a_detector_ablation.csv")
    if not a.empty:
        a["cohort"] = a["stock"].map(cohort)
        rows = []
        for (coh, det), g in a.groupby(["cohort", "detector"]):
            tp, fp, fn = g["tp"].sum(), g["fp"].sum(), g["fn"].sum()
            withpos = g[(g["tp"] + g["fn"]) > 0]
            rows.append({"cohort": coh, "detector": det, "stocks": g["stock"].nunique(),
                         "stocks_with_positives": withpos["stock"].nunique(),
                         "pooled_precision": tp / (tp + fp) if tp + fp else 0.0,
                         "pooled_recall": tp / (tp + fn) if tp + fn else 0.0,
                         "pooled_f1": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0,
                         "median_f1": withpos["f1"].median(), "q1_f1": withpos["f1"].quantile(.25),
                         "q3_f1": withpos["f1"].quantile(.75), "median_alarm_rate": g["alarm_rate"].median()})
        da = pd.DataFrame(rows)
        da.to_csv(agg / "agg_daily_detection.csv", index=False)
        ho = a[(a["cohort"] == "held-out") & ((a["tp"] + a["fn"]) > 0)]
        wide = ho.pivot_table(index="stock", columns="detector", values="f1")
        for other in ["Baseline: return Z-score", "Baseline: Isolation Forest", "Ablation: band severity only",
                      "Ablation: volume-scaled score only"]:
            if PROPOSED_A in wide and other in wide:
                n, w, p, r = wilcoxon(wide[PROPOSED_A], wide[other])
                tests.append({"experiment": "A daily F1", "comparison": f"proposed vs {other}", "n_stocks": n,
                              "W": w, "p": p, "rank_biserial": r,
                              "median_diff": float((wide[PROPOSED_A] - wide[other]).median())})
        h = da[da["cohort"] == "held-out"].set_index("detector")
        if len(h):
            tex.append(r"""\begin{table}[!t]
\caption{Daily Detection on Held-Out CSE Stocks (Past-Only Labels)}
\label{tab:ms_daily}
\centering\footnotesize\setlength{\tabcolsep}{2.4pt}
\begin{tabular}{@{}lrrrc@{}}
\toprule
Detector & Prec. & Rec. & F1 & Median F1 [IQR] \\
\midrule""")
            order_a = [PROPOSED_A, "Ablation: volume-scaled score only", "Ablation: band severity only",
                       "Ablation: unscaled |residual|", "Ablation: robust residual z (MAD)",
                       "Baseline: return Z-score", "Baseline: Isolation Forest"]
            for det in [d_ for d_ in order_a if d_ in h.index]:
                r_ = h.loc[det]
                tex.append(f"{det.split(': ',1)[-1].replace('|', '$|$')} & {r_.pooled_precision:.3f} & {r_.pooled_recall:.3f} & {r_.pooled_f1:.3f} & "
                           f"{r_.median_f1:.2f} [{r_.q1_f1:.2f}--{r_.q3_f1:.2f}] \\\\")
            n_st = int(h["stocks"].max())
            tex.append(r"\bottomrule" + "\n" + r"\end{tabular}" + "\n" + r"\vspace{2pt}" + "\n" +
                       r"\parbox{\columnwidth}{\scriptsize Pooled precision/recall/F1 over " + str(n_st) +
                       r" held-out stocks; median F1 over stocks with at least one test positive.}" + "\n" + r"\end{table}" + "\n")

    # ---------------- model selection (persistence frequency)
    meta = load(per, "exp_a_run_metadata.csv")
    if not meta.empty:
        meta["cohort"] = meta["stock"].map(cohort)
        meta["mae_ratio"] = meta["test_mae_model"] / meta["test_mae_persistence"]
        ms = meta.groupby("cohort").agg(stocks=("stock", "nunique"),
                                        share_persistence_selected=("return_blend", lambda s: float((s == 0).mean())),
                                        median_mae_ratio=("mae_ratio", "median"),
                                        share_beats_persistence=("mae_ratio", lambda s: float((s < 0.99).mean()))).reset_index()
        ms.to_csv(agg / "agg_model_selection.csv", index=False)

    # ---------------- Exp B: documented episodes
    b = load(per, "exp_b_episode_detection.csv")
    if not b.empty:
        b["cohort"] = b["stock"].map(cohort)
        eps = [c[:2] for c in b.columns if c.endswith("_detected") and c[0] == "E"]
        rows = []
        for (coh, det), g in b.groupby(["cohort", "detector"]):
            det_flags = pd.concat([g[f"{e}_detected"].astype(bool) for e in eps])
            delays = pd.concat([g[f"{e}_delay_days"] for e in eps]).dropna()
            rows.append({"cohort": coh, "detector": det, "stocks": g["stock"].nunique(),
                         "stock_episodes": int(len(det_flags)), "detection_rate": float(det_flags.mean()),
                         **{f"{e}_rate": float(g[f"{e}_detected"].astype(bool).mean()) for e in eps},
                         "median_delay": float(delays.median()) if len(delays) else np.nan,
                         "median_fa_per_100": float(g["false_alarms_per_100_days"].median()),
                         "q1_fa": float(g["false_alarms_per_100_days"].quantile(.25)),
                         "q3_fa": float(g["false_alarms_per_100_days"].quantile(.75))})
        db = pd.DataFrame(rows)
        db.to_csv(agg / "agg_episode_detection.csv", index=False)
        ho = b[b["cohort"] == "held-out"]
        fa = ho.pivot_table(index="stock", columns="detector", values="false_alarms_per_100_days")
        hits = ho.assign(hits=ho["episodes_detected"]).pivot_table(index="stock", columns="detector", values="hits")
        for other in ["Daily: return Z-score", "Daily: robust residual z", "Daily: volume-scaled score",
                      "Pattern: two-sided CUSUM"]:
            if PROPOSED_B in fa and other in fa:
                n, w, p, r = wilcoxon(fa[PROPOSED_B], fa[other])
                tests.append({"experiment": "B false alarms/100", "comparison": f"proposed vs {other}", "n_stocks": n,
                              "W": w, "p": p, "rank_biserial": r, "median_diff": float((fa[PROPOSED_B] - fa[other]).median())})
                n, w, p, r = wilcoxon(hits[PROPOSED_B], hits[other])
                tests.append({"experiment": "B episodes detected", "comparison": f"proposed vs {other}", "n_stocks": n,
                              "W": w, "p": p, "rank_biserial": r, "median_diff": float((hits[PROPOSED_B] - hits[other]).median())})
        h = db[db["cohort"] == "held-out"].set_index("detector")
        if len(h):
            tex.append(r"""\begin{table}[!t]
\caption{Documented-Episode Detection on Held-Out CSE Stocks}
\label{tab:ms_episodes}
\centering\footnotesize\setlength{\tabcolsep}{2.6pt}
\begin{tabular}{@{}lrrrc@{}}
\toprule
Detector & Det.\,\% & E1/E2/E3\,\% & Delay & FA/100 [IQR] \\
\midrule""")
            order_b = ["Daily: return Z-score", "Daily: volume-scaled score", "Daily: robust residual z", PROPOSED_B,
                       "Pattern: two-sided CUSUM", "Pattern: EWMA residual"]
            for det in [d_ for d_ in order_b if d_ in h.index]:
                r_ = h.loc[det]
                per_ep = "/".join(f"{100 * r_[f'{e}_rate']:.0f}" for e in eps)
                tex.append(f"{det.split(': ',1)[-1]} & {100 * r_.detection_rate:.0f} & {per_ep} & {r_.median_delay:.0f} & "
                           f"{r_.median_fa_per_100:.2f} [{r_.q1_fa:.2f}--{r_.q3_fa:.2f}] \\\\")
            tex.append(r"\bottomrule" + "\n" + r"\end{tabular}" + "\n" + r"\vspace{2pt}" + "\n" +
                       r"\parbox{\columnwidth}{\scriptsize Thresholds fixed on 2016--2018 residuals at a 2\% alarm budget. Delay: median sessions from episode start. FA: alarms per 100 out-of-episode sessions, 2019--2026.}"
                       + "\n" + r"\end{table}" + "\n")

    # ---------------- Exp D: pattern enrichment
    p = load(per, "exp_d_pattern_profiles.csv")
    n = load(per, "exp_d_null_rates.csv")
    if not p.empty and not n.empty:
        p["cohort"] = p["stock"].map(cohort)
        n["cohort"] = n["stock"].map(cohort)
        labs = ["shock-dominated", "persistent drift down", "persistent drift up", "volatility burst"]
        rows = []
        for (coh, win), g in p.groupby(["cohort", "window"]):
            row = {"cohort": coh, "window": win, "stocks": g["stock"].nunique(),
                   "any_label_rate": float((g["pattern"] != "none").mean()),
                   "median_price_change_pct": float(g["price_change_pct"].median())}
            for lab in labs:
                row[f"rate_{lab}"] = float(g["pattern"].fillna("").str.contains(lab).mean())
            null = n[n["cohort"] == coh]
            null_any = float(null["rate_any"].mean()) if len(null) else np.nan
            k, m = int((g["pattern"] != "none").sum()), int(len(g))
            row["null_any_rate"] = null_any
            row["binom_p_vs_null"] = float(stats.binomtest(k, m, min(max(null_any, 1e-6), 1 - 1e-6), alternative="greater").pvalue) if m and np.isfinite(null_any) else np.nan
            rows.append(row)
        dp = pd.DataFrame(rows)
        dp.to_csv(agg / "agg_pattern_enrichment.csv", index=False)
        h = dp[dp["cohort"] == "held-out"]
        if len(h):
            tex.append(r"""\begin{table}[!t]
\caption{Deviation-Pattern Labels on Held-Out Stocks (Rules Frozen on 2016--2018)}
\label{tab:ms_patterns}
\centering\footnotesize\setlength{\tabcolsep}{2.2pt}
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
Window & Any\,\% & Shock & Drift$\downarrow$ & Drift$\uparrow$ & Burst & $p$ \\
\midrule""")
            for _, r_ in h.iterrows():
                tex.append(f"{r_.window} & {100 * r_.any_label_rate:.0f} & {100 * r_['rate_shock-dominated']:.0f} & "
                           f"{100 * r_['rate_persistent drift down']:.0f} & {100 * r_['rate_persistent drift up']:.0f} & "
                           f"{100 * r_['rate_volatility burst']:.0f} & {r_.binom_p_vs_null:.1g} \\\\")
            null_txt = f"{100 * h['null_any_rate'].iloc[0]:.1f}"
            tex.append(r"\bottomrule" + "\n" + r"\end{tabular}" + "\n" + r"\vspace{2pt}" + "\n" +
                       r"\parbox{\columnwidth}{\scriptsize Percent of stocks receiving each label. Out-of-episode windows received any label at a rate of "
                       + null_txt + r"\%; $p$: one-sided binomial test of the episode rate against that rate.}" + "\n" + r"\end{table}" + "\n")

    # ---------------- tests
    if tests:
        t = pd.DataFrame(tests)
        ok = t["p"].notna()
        t.loc[ok, "p_holm"] = holm(t.loc[ok, "p"].tolist())
        t.to_csv(agg / "agg_paired_tests.csv", index=False)
    (agg / "tables_generated.tex").write_text("\n".join(tex))
    print(f"Aggregated {inc['evaluated']} evaluated stocks into {agg}")
    for f in sorted(agg.glob("*.csv")):
        print(" -", f.name)


if __name__ == "__main__":
    main()
