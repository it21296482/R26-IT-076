"""Analyse user-study responses (pre-specified in STUDY_PROTOCOL.md).

    python research/user_study/analyse_study.py [responses_folder]

Reads every *.json session file (single sessions or the "Download all" array),
removes duplicates by participant ID, and writes results/ with:
  per_participant.csv, per_question.csv, results.json, results_table.tex
Primary outcome: comprehension score (0-5), system vs chart-only, Wilcoxon signed-rank.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
Q_LABELS = ["Q1 price change", "Q2 behaviour vs pattern", "Q3 calm day ≠ no problem", "Q4 forecast uncertainty", "Q5 no buy/sell advice"]


def load(folder: Path) -> list[dict]:
    sessions = {}
    for f in sorted(folder.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for s in data if isinstance(data, list) else [data]:
            sessions[s["participant_id"]] = s
    return list(sessions.values())


def paired(x: np.ndarray, y: np.ndarray) -> dict:
    d = x - y
    nz = d[d != 0]
    out = {"n": int(len(d)), "mean_system": float(x.mean()), "mean_chart": float(y.mean()),
           "median_diff": float(np.median(d)), "mean_diff": float(d.mean())}
    if len(nz) >= 5:
        w = stats.wilcoxon(x, y, zero_method="wilcox", alternative="two-sided")
        ranks = stats.rankdata(np.abs(nz))
        out.update({"W": float(w.statistic), "p": float(w.pvalue),
                    "rank_biserial": float((ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum())})
    # bootstrap 95% CI of the mean difference (participants resampled)
    rng = np.random.default_rng(42)
    boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
    out["mean_diff_ci"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    return out


def holm_adjust(values: list[float]) -> list[float]:
    """Holm adjustment in sorted order, preserving monotonicity."""
    result = np.full(len(values), np.nan)
    valid = [i for i, value in enumerate(values) if np.isfinite(value)]
    running = 0.0
    for rank, index in enumerate(sorted(valid, key=lambda i: values[i])):
        running = max(running, min(1.0, (len(valid) - rank) * values[index]))
        result[index] = running
    return result.tolist()


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "responses"
    sessions = load(folder)
    if not sessions:
        raise SystemExit(f"No session files in {folder}")
    rows = []
    for s in sessions:
        for p in s["parts"]:
            rows.append({"participant": s["participant_id"], "group": s["group"], "language": s["language"],
                         "order": p["order"], "company": p["company"], "condition": p["condition"],
                         "score": p["score"], "interp_score": sum(p["correct"][1:4]), "confidence": p["confidence"],
                         "understood": p["likert"][0], "useful": p["likert"][1], "easy": p["likert"][2],
                         "seconds": p["seconds"], "not_sure": sum(a == len_ - 1 for a, len_ in zip(p["answers"], [5, 5, 3, 4, 4])),
                         **{f"q{i + 1}": int(c) for i, c in enumerate(p["correct"])},
                         "pref": s["final"]["pref"], "bought": s["final"]["bought"], "knowledge": s["final"]["knowledge"]})
    df = pd.DataFrame(rows)
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "per_participant.csv", index=False)
    wide = df.pivot_table(index="participant", columns="condition",
                          values=["score", "interp_score", "confidence", "understood", "useful", "easy", "seconds", "not_sure"])
    wide = wide.dropna()
    res = {"participants": int(wide.shape[0]), "languages": df.drop_duplicates("participant")["language"].value_counts().to_dict(),
           "groups": df.drop_duplicates("participant")["group"].value_counts().sort_index().to_dict(),
           "novices": int((df.drop_duplicates("participant")["bought"] == 1).sum())}
    tests = {}
    for m in ["score", "interp_score", "confidence", "understood", "useful", "easy", "seconds", "not_sure"]:
        tests[m] = paired(wide[(m, "system")].to_numpy(float), wide[(m, "chart")].to_numpy(float))
    secondary = ["interp_score", "confidence", "understood", "useful", "easy"]
    adjusted = holm_adjust([tests[m].get("p", np.nan) for m in secondary])
    for m, corrected in zip(secondary, adjusted):
        if "p" in tests[m]:
            tests[m]["p_holm"] = corrected
    res["tests"] = tests
    # carry-over check: system-first vs chart-first difference in chart-only scores
    first = df[df["order"] == 1].set_index("participant")["condition"]
    chart_scores = df[df["condition"] == "chart"].set_index("participant")["score"]
    g1 = chart_scores[first.reindex(chart_scores.index) == "system"]
    g2 = chart_scores[first.reindex(chart_scores.index) == "chart"]
    if len(g1) >= 3 and len(g2) >= 3:
        mw = stats.mannwhitneyu(g1, g2, alternative="two-sided")
        res["carryover_chart_score"] = {"system_first_mean": float(g1.mean()), "chart_first_mean": float(g2.mean()), "p": float(mw.pvalue)}
    pq = df.groupby("condition")[[f"q{i}" for i in range(1, 6)]].mean().T
    pq.index = Q_LABELS
    pq.to_csv(out / "per_question.csv")
    pref = df.drop_duplicates("participant")["pref"].value_counts().reindex([0, 1, 2], fill_value=0)
    res["preference"] = {"chart_only": int(pref[0]), "system": int(pref[1]), "no_difference": int(pref[2])}
    if pref[0] + pref[1] > 0:
        res["preference"]["sign_test_p"] = float(stats.binomtest(int(pref[1]), int(pref[0] + pref[1]), 0.5).pvalue)
    (out / "results.json").write_text(json.dumps(res, indent=2))

    t = res["tests"]
    def line(name, m, fmt="{:.2f}"):
        r = t[m]
        p = r.get("p_holm", r.get("p", float("nan")))
        return (f"{name} & {fmt.format(r['mean_chart'])} & {fmt.format(r['mean_system'])} & "
                f"{fmt.format(r['mean_diff'])} [{fmt.format(r['mean_diff_ci'][0])}, {fmt.format(r['mean_diff_ci'][1])}] & "
                f"{r.get('rank_biserial', float('nan')):.2f} & {p:.3f} \\\\")
    tex = [r"\begin{table}[!t]", r"\caption{User Study: Chart Only vs.\ System Explanation (n=" + str(res["participants"]) + r", Within-Subjects)}",
           r"\label{tab:userstudy}", r"\centering\footnotesize\setlength{\tabcolsep}{2.4pt}",
           r"\begin{tabular}{@{}lrrcrr@{}}", r"\toprule", r"Measure & Chart & System & Diff.\ [95\% CI] & $r$ & $p$ \\", r"\midrule",
           line("Comprehension (0--5)", "score"), line("Interpretation Q2--Q4 (0--3)", "interp_score"),
           line("Confidence (1--5)", "confidence"), line("Understood (1--7)", "understood"),
           line("Useful (1--7)", "useful"), line("Easy (1--7)", "easy"), line("Time (s)", "seconds", "{:.0f}"),
           r"\bottomrule", r"\end{tabular}", r"\vspace{2pt}",
           r"\parbox{\columnwidth}{\scriptsize Wilcoxon signed-rank tests; $r$: matched-pairs rank-biserial. Secondary outcomes Holm-adjusted. CI: participant bootstrap of the mean difference.}",
           r"\end{table}"]
    (out / "results_table.tex").write_text("\n".join(tex))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
