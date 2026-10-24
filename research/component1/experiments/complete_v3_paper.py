"""Build an evidence-checked manuscript; never invent missing study results.

--watch rebuilds once the already-running held-out queue finishes. It does not
recruit participants, modify models, write MongoDB or submit/push a paper.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "research/component1/artifacts/paper_v3_verified"
PROJECT = ROOT / "output/ieee-component1-paper-v3"
EXPORTS = ROOT / "research/component1/data/actuals_all"
FINAL = ROOT / "output/pdf/IT21296482_Component1_IEEE_Paper_v3_Evidence_Checked_R26-IT-076.pdf"
SOURCE = ROOT / "output/IT21296482_Component1_IEEE_Paper_v3_Source_R26-IT-076.zip"
OR_A = "Proposed: score OR band (past-only adaptive)"
OR_B = "Daily: proposed score OR band"
LABELS = {
    OR_A: "Adaptive score OR band",
    "Ablation: volume-scaled score only": "Volume score only",
    "Ablation: band severity only": "Band only",
    "Ablation: unscaled |residual|": r"Unscaled $|D_t|$",
    "Ablation: robust residual z (MAD)": r"Robust $|z_t|$",
    "Baseline: return Z-score": "Return Z-score",
    "Baseline: Isolation Forest": "Isolation Forest",
}


def table(caption, label, columns, heading, rows, note=""):
    return "\n".join([
        r"\begin{table}[!t]", r"\caption{" + caption + "}",
        r"\label{" + label + "}", r"\centering\footnotesize",
        r"\setlength{\tabcolsep}{2.7pt}", r"\begin{tabular}{@{}" + columns + r"@{}}",
        r"\toprule", heading + r" \\", r"\midrule", *rows, r"\bottomrule",
        r"\end{tabular}",
        (r"\parbox{\columnwidth}{\scriptsize " + note + "}") if note else "",
        r"\end{table}",
    ])


def build(compile_pdf=True):
    manifest = json.loads((EXPORTS / "export_manifest.json").read_text())
    exports = [row for row in manifest["results"] if row["status"] == "exported"]
    audit = []
    for row in manifest["results"]:
        item = dict(row)
        item["development"] = row["symbol"].split(".")[0] in {"JKH", "BIL"}
        if row["status"] == "exported":
            history = pd.read_csv(EXPORTS / row["file"], parse_dates=["date"])
            import paper_experiments as pe
            item["eligible"], item["eligibility_reason"] = pe.eligibility(history)
        else:
            item["eligible"] = False
            item["eligibility_reason"] = row["reason"]
        audit.append(item)
    logs = RESULTS / "run_log_heldout.csv"
    log = pd.read_csv(logs).drop_duplicates("stock", keep="last") if logs.exists() else pd.DataFrame(
        columns=["stock", "status"])
    completed = log.loc[log.status == "done", "stock"].tolist()
    failed = int((log.status == "failed").sum())
    target = sum(row["eligible"] and not row["development"] for row in audit)
    expected = sum(not row["development"] for row in audit if row["status"] == "exported")
    source_complete = len({row["symbol"] for row in audit}) == manifest["listings"]
    finished = source_complete and len(log) >= expected
    receipt = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "listings": manifest["listings"],
        "source_attempts": len(audit), "exported": len(exports),
        "eligible_including_development": sum(row["eligible"] for row in audit),
        "heldout_eligible": target, "heldout_completed": len(completed),
        "heldout_failed": failed, "heldout_pending": target - len(completed) - failed,
        "batch_finished": finished, "participant_results_supplied": False,
        "frozen_code_commit": "0ae9f9b", "queue_commit": "0965ec9",
    }
    import numpy, scipy, sklearn, torch
    receipt["software_versions"] = {module.__name__: module.__version__
                                    for module in (numpy, pd, scipy, sklearn, torch)}
    RESULTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audit).to_csv(RESULTS / "source_inclusion_audit.csv", index=False)
    pd.DataFrame(audit).to_csv(PROJECT / "source_inclusion_audit.csv", index=False)
    (PROJECT / "completion_receipt.json").write_text(json.dumps(receipt, indent=2))

    rows = []
    for stock in ("JKH", "BIL"):
        df = pd.read_csv(RESULTS / "per_stock" / stock / "exp_a_detector_ablation.csv")
        n = int(df.iloc[0][["tp", "fp", "fn", "tn"]].sum())
        rows.append(r"\multicolumn{6}{l}{\textit{" + stock + f" ({n} test sessions)" + r"}}\\")
        for _, r in df.iterrows():
            if r.detector not in LABELS:
                continue
            rows.append(f"{LABELS[r.detector]} & {int(r.tp)}/{int(r.fp)} & "
                        f"{r.precision:.3f} & {r.recall:.3f} & {r.f1:.3f} & "
                        f"{r.f1_ci_low:.2f}--{r.f1_ci_high:.2f}" + r" \\")
    (PROJECT / "development_daily_table.tex").write_text(table(
        "Reproduced Development-Stock Daily Detection (12 Proxy Positives Each)",
        "tab:ablation", "lrrrrr", r"Detector & TP/FP & Pr. & Re. & F1 & 95\% CI", rows))

    explanation = pd.read_csv(RESULTS / "exp_e_explanations.csv")
    names = {"volume_ratio_20d": "Volume ratio", "return_1d": "Return",
             "range_pct": "Range", "atr_14": "ATR(14)"}
    rows = []
    for _, r in explanation.iterrows():
        target_name = "log(1+score)" if "log1p" in r.target else "Band severity"
        factors = f"{names.get(r.top1, r.top1)} {r.top1_share_pct:.1f}; {names.get(r.top2, r.top2)} {r.top2_share_pct:.1f}"
        rows.append(f"{r.stock} & {target_name} & {r.test_r2:.2f} & {r.test_spearman:.2f} & {factors} & {r.esi_mean:.2f}" + r" \\")
    (PROJECT / "explanation_table.tex").write_text(table(
        "Development-Stock Test-Set Surrogate Fidelity and Attribution Shares",
        "tab:explain", "llrrlr", r"Stock & Target & $R^2$ & $\rho$ & Factors (\%) & ESI", rows,
        "Volume score target is log(1+min(score, $10^6$)). Shares average absolute "
        "Tree-SHAP magnitudes over test rows; they are not causal effects."))

    counts = [
        ["Current directory listings", manifest["listings"]],
        ["Histories exported / source exclusions", f"{len(exports)} / {manifest['listings']-len(exports)}"],
        ["Eligible / data-eligibility exclusions", f"{sum(r['eligible'] for r in audit)} / {len(exports)-sum(r['eligible'] for r in audit)}"],
        ["Development securities", 2],
        ["Eligible held-out securities", target],
        ["Held-out runs completed / failed", f"{len(completed)} / {failed}"],
        ["Eligible held-out runs pending", receipt["heldout_pending"]],
    ]
    (PROJECT / "inclusion_table.tex").write_text(table(
        "Source Audit and Execution Status at Manuscript Generation", "tab:inclusion", "lr",
        "Stage & Securities", [f"{a} & {b}" + r" \\" for a, b in counts],
        "Snapshot: " + receipt["generated_at"][:16].replace("T", " ") +
        " UTC. The inventory is current at acquisition, not a historical point-in-time listing universe."))
    if not finished:
        abstract = "The all-listing source audit is complete, but its held-out model evaluation remains in progress; no completed replication or participant study is claimed."
        paragraph = (
            f"The source audit attempted all {manifest['listings']} listed securities and exported {len(exports)} histories; "
            f"{target} non-development securities met the fixed eligibility conditions. "
            f"At this manuscript snapshot, {len(completed)} held-out runs were complete, {failed} had failed and "
            f"{receipt['heldout_pending']} eligible runs remained pending. Table~\\ref{{tab:inclusion}} records that status. "
            "Intermediate results are deliberately not used to claim replication. The bounded queue continues "
            "without changing the statistical rules; an updated manuscript can be rebuilt when the cohort finishes.")
        heldout_table = ""
        conclusion = "Broader replication is underway on the source-audited eligible cohort; no final cross-stock performance claim is yet made."
    else:
        all_a = pd.concat([pd.read_csv(RESULTS / "per_stock" / c / "exp_a_detector_ablation.csv") for c in completed])
        all_b = pd.concat([pd.read_csv(RESULTS / "per_stock" / c / "exp_b_episode_detection.csv") for c in completed])
        rows = []
        for det in LABELS:
            g = all_a[all_a.detector == det]
            if g.empty:
                continue
            tp, fp, fn = g.tp.sum(), g.fp.sum(), g.fn.sum()
            pooled = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
            positive = g[(g.tp + g.fn) > 0]
            rows.append(f"{LABELS[det]} & {pooled:.3f} & {positive.f1.median():.3f}" + r" \\")
        heldout_table = table("Completed Held-Out Daily Detection", "tab:heldout", "lrr",
                             "Detector & Pooled F1 & Median F1", rows,
                             "Median excludes stocks with no proxy positives. Securities share market dates; results are not independent replications.")
        combined = all_b[all_b.detector == OR_B]
        observed = sum((combined[f"E{i}_trading_days"] > 0).sum() for i in (1, 2, 3))
        hits = sum(combined.loc[combined[f"E{i}_trading_days"] > 0, f"E{i}_detected"].sum() for i in (1, 2, 3))
        rate = hits / observed if observed else float("nan")
        fa = combined.false_alarms_per_100_days.median()
        abstract = f"The completed exploratory replication covers {len(completed)} additional securities; independent participant evaluation remains future work."
        paragraph = (
            f"All {manifest['listings']} listings were attempted: {len(exports)} histories were exported and "
            f"{target} held-out securities met eligibility. The queue completed {len(completed)} and recorded "
            f"{failed} failures. Table~\\ref{{tab:heldout}} reports daily detection. The fixed-budget combined rule "
            f"flagged {100*rate:.1f}\\% of {observed} stock--period cases with actual observations, with median "
            f"{fa:.2f} out-of-episode alerts per 100 sessions. These are descriptive associations with shared "
            "market events, not independent causal detections. Source and model exclusions restrict generalisation.")
        conclusion = f"The completed {len(completed)}-security extension is descriptive, with shared-event dependence and source eligibility limiting generalisation."
    (PROJECT / "heldout_table.tex").write_text(heldout_table)
    macros = {"ReplicationAbstract": abstract, "ReplicationResults": paragraph,
              "ReplicationConclusion": conclusion}
    (PROJECT / "verified_results.tex").write_text("\n".join(
        r"\newcommand{\%s}{%s}" % (name, text) for name, text in macros.items()))
    if compile_pdf:
        compiler = shutil.which("tectonic") or "/private/tmp/tectonic"
        subprocess.run([compiler, "--keep-logs", "main.tex"], cwd=PROJECT, check=True)
        import pymupdf
        doc = pymupdf.open(PROJECT / "main.pdf")
        if len(doc) > 6:
            raise ValueError(f"Manuscript has {len(doc)} pages; six-page limit exceeded.")
        text = "".join(page.get_text() for page in doc)
        if "[N]" in text or "[n]" in text or "Report:" in text:
            raise ValueError("Unresolved manuscript placeholders.")
        FINAL.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT / "main.pdf", FINAL)
        with zipfile.ZipFile(SOURCE, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file in PROJECT.iterdir():
                if file.is_file() and file.suffix in {".tex", ".bib", ".cls", ".bst", ".pdf", ".json", ".md", ".csv"}:
                    archive.write(file, file.name)
        print("PDF:", FINAL, "pages:", len(doc), flush=True)
    print(json.dumps(receipt), flush=True)
    return finished


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    finished = build()
    while args.watch and not finished:
        time.sleep(120)
        # Rebuild the manuscript only after the full planned execution is done.
        m = json.loads((EXPORTS / "export_manifest.json").read_text())
        expected = sum(row["status"] == "exported" and row["symbol"].split(".")[0] not in {"JKH", "BIL"}
                       for row in m["results"])
        p = RESULTS / "run_log_heldout.csv"
        if p.exists() and len(pd.read_csv(p).drop_duplicates("stock")) >= expected:
            subprocess.run([__import__("sys").executable, str(Path(__file__).with_name("aggregate_results.py"))],
                           check=True)
            finished = build()
