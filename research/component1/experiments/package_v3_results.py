"""Package completed replication evidence without vendor histories or participants.

Use --wait while the existing queue runs. This does not retry failed models,
change their frozen rules, submit the paper, or publish the evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "research/component1/artifacts/paper_v3_verified"
MANIFEST = ROOT / "research/component1/data/actuals_all/export_manifest.json"
OUTPUT = ROOT / "output/Component1_V3_Completed_Results_R26-IT-076.zip"
DEV = {"JKH_N0000", "BIL_N0000"}


def execution_status():
    manifest = json.loads(MANIFEST.read_text())
    expected = {row["symbol"].replace(".", "_") for row in manifest["results"]
                if row["status"] == "exported"} - DEV
    log = pd.read_csv(RESULTS / "run_log_heldout.csv")
    if log.stock.duplicated().any():
        raise ValueError("Duplicate stock execution records require review.")
    if not set(log.status).issubset({"done", "failed", "excluded"}):
        raise ValueError("Unknown execution status.")
    if not set(log.stock).issubset(expected):
        raise ValueError("Run log contains securities outside the source cohort.")
    complete = (manifest.get("directoryComplete") is True
                and len({r["symbol"] for r in manifest["results"]}) == manifest["listings"]
                and expected == set(log.stock))
    return complete, manifest, log, expected


def package():
    complete, manifest, log, expected = execution_status()
    if not complete:
        raise ValueError("The planned queue is incomplete; no final package created.")
    subprocess.run([sys.executable, str(Path(__file__).with_name("aggregate_results.py"))],
                   check=True)
    inclusion = pd.read_csv(RESULTS / "aggregate/inclusion.csv").iloc[0]
    if not bool(inclusion.execution_complete):
        raise ValueError("Aggregate inclusion does not confirm completed execution.")
    files = {str(p.relative_to(RESULTS)): p.read_bytes()
             for p in (RESULTS / "aggregate").glob("*") if p.is_file()}
    summary_names = ("exp_a_detector_ablation.csv", "exp_a_run_metadata.csv",
                     "exp_b_episode_detection.csv", "exp_b_thresholds.csv",
                     "exp_b_walk_forward_fits.csv", "exp_d_pattern_profiles.csv",
                     "exp_d_null_rates.csv")
    for stock in log.loc[log.status.eq("done"), "stock"].tolist() + ["JKH", "BIL"]:
        for name in summary_names:
            path = RESULTS / "per_stock" / stock / name
            files[str(path.relative_to(RESULTS))] = path.read_bytes()
    for name in ("run_log.csv", "run_log_heldout.csv", "heldout_execution_manifest.json",
                 "run_metadata.json", "frozen_pattern_rules.json", "source_inclusion_audit.csv",
                 "exp_e_explanations.csv"):
        files[name] = (RESULTS / name).read_bytes()
    files["export_manifest.json"] = MANIFEST.read_bytes()
    failures = log.loc[log.status.eq("failed")]
    files["failure_details.csv"] = failures.to_csv(index=False).encode()
    receipt = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_complete": True, "listings": manifest["listings"],
        "exported": sum(r["status"] == "exported" for r in manifest["results"]),
        "heldout_queue_tasks": len(expected),
        "heldout_completed": int(log.status.eq("done").sum()),
        "heldout_failed": len(failures),
        "heldout_excluded": int(log.status.eq("excluded").sum()),
        "participant_results": "not supplied; study remains future work",
        "omissions": ["raw vendor OHLCV histories", "participant records", "model weights"],
    }
    files["package_receipt.json"] = json.dumps(receipt, indent=2).encode()
    files["README.md"] = (
        "# Completed Component 1 V3 Evaluation\n\n"
        "All planned source exports have a terminal execution record. Completed execution "
        "does not mean every eligible security fitted successfully: retain the failures "
        "and exclusions in the paper's cohort definition.\n\n"
        "aggregate/ contains the tables and CSV statistics; per_stock/ contains the "
        "completed-security summary metrics used to check those aggregates. "
        "run_log_heldout.csv records "
        "all held-out tasks; failure_details.csv retains their exact failure reasons. "
        "export_manifest.json records all source attempts, including exclusions. "
        "The two development securities are separate in run_log.csv.\n\n"
        "Paired tests are exploratory because securities share companies, trading dates "
        "and market events. Proxy labels are not expert-verified anomaly ground truth. "
        "Outside-event alerts are not independently confirmed false positives. "
        "Pattern frequencies are descriptive. No participant study is reported.\n\n"
        "The SHA256SUMS file fingerprints every other archive member. Raw market histories "
        "and participant records are intentionally excluded.\n"
    ).encode()
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, data in sorted(files.items())).encode()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".pending")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    temporary.replace(OUTPUT)
    print(json.dumps(receipt), flush=True)
    print("Evidence package:", OUTPUT, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    previous = None
    while True:
        complete, _, log, expected = execution_status()
        counts = log.status.value_counts().to_dict()
        counts["unprocessed_tasks"] = len(expected) - len(log)
        if counts != previous:
            print(json.dumps(counts), flush=True)
            previous = counts
        if complete:
            package()
            break
        if not args.wait:
            raise SystemExit("Queue incomplete; rerun with --wait or after completion.")
        time.sleep(60)
