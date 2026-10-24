"""Fig. 2 of the revised paper: cumulative deviation paths with alarms in stress windows."""
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "paper_v3_verified"
dest = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "fig_pattern_monitor.pdf"
colors = {"JKH": "#235A8C", "BIL": "#BF6619"}
windows = [("E2 COVID-19 (9 Mar-15 May 2020)", "2020-03-09", "2020-05-15"),
           ("E3 sovereign crisis (Mar-Jul 2022)", "2022-03-01", "2022-07-31"),
           ("Unlabelled (8 May-28 Aug 2026)", "2026-05-08", "2026-08-28")]
plt.rcParams.update({"font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix", "pdf.fonttype": 42,
                     "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5,
                     "ytick.labelsize": 6.5, "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5})
fig, axes = plt.subplots(1, 3, figsize=(7.0, 1.95), sharey=True)
data = {c: pd.read_csv(OUT / "per_stock" / c / "walk_forward_residuals.csv", parse_dates=["date"]) for c in colors}
for ax, (title, a, b) in zip(axes, windows):
    ymin = 0
    ends = []
    for k, (code, wf) in enumerate(data.items()):
        w = wf[(wf.date >= a) & (wf.date <= b)].reset_index(drop=True)
        cum = (np.exp(np.log1p(w.rel_resid).cumsum()) - 1) * 100
        x = np.arange(1, len(w) + 1)
        ax.plot(np.r_[0, x], np.r_[0, cum], color=colors[code], lw=1.4)
        d = w.daily_alarm.astype(bool).to_numpy()
        cu = w.cusum_alarm.astype(bool).to_numpy()
        ax.plot(x[cu], cum[cu], "D", ms=5.0, mfc="white", mec=colors[code], mew=0.9, zorder=3)
        ax.plot(x[d], cum[d], "o", ms=2.6, mfc="#111111", mec="none", zorder=4)
        ends.append((code, x[-1], cum.iloc[-1]))
    ends.sort(key=lambda e: e[2])
    for i, (code, xe, ye) in enumerate(ends):
        shift = 0
        if i == 1 and abs(ends[1][2] - ends[0][2]) < 8:
            shift = 7
        if i == 0 and abs(ends[1][2] - ends[0][2]) < 8:
            shift = -5
        ax.annotate(f"{code} {ye:+.1f}%", (xe, ye), xytext=(3, shift), textcoords="offset points",
                    color="#333333", fontsize=6.5, va="center", ha="left")
    ax.axhline(0, color="#999999", lw=0.5)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True, nbins=5))
    ax.set_title(title, pad=3)
    ax.set_xlabel("Trading sessions in window")
    ax.grid(axis="y", color="#e8e8e8", lw=0.4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(0, ax.get_xlim()[1] * 1.28)
axes[0].set_ylabel("Cumulative deviation (%)")
from matplotlib.lines import Line2D
h = [Line2D([], [], color=colors["JKH"], lw=1.4), Line2D([], [], color=colors["BIL"], lw=1.4),
     Line2D([], [], ls="", marker="o", ms=2.6, mfc="#111111", mec="none"),
     Line2D([], [], ls="", marker="D", ms=5.0, mfc="white", mec="#555555")]
fig.legend(h, ["JKH", "BIL", "Daily OR-rule alarm", "CUSUM alarm"], loc="lower center", ncol=4, frameon=False,
           fontsize=6.5, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.08, 1, 1), w_pad=0.8)
fig.savefig(dest, bbox_inches="tight")
fig.savefig(dest.with_suffix(".png"), dpi=200, bbox_inches="tight")
print("saved", dest)
