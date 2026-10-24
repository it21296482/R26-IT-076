"""Evaluate arriving read-only exports with bounded independent stock workers.

No model/rule selection occurs here. Statistical settings live in the frozen
paper_experiments.py and pattern_rules.py. This process never connects to MongoDB.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[key] = "1"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def evaluate(code, path, out):
    import pandas as pd
    import paper_experiments as pe
    raw = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    ok, reason = pe.eligibility(raw)
    if not ok:
        return {"stock": code, "status": "excluded", "reason": reason,
                "rows": len(raw), "input_sha256": digest}
    try:
        result = pe.run_stock(code, raw, Path(out) / "per_stock" / code, {"C"}, False)
        result["input_sha256"] = digest
        return result
    except Exception as error:
        return {"stock": code, "status": "failed", "reason": repr(error)[:500],
                "rows": len(raw), "input_sha256": digest}


def main():
    import pandas as pd
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--manifest", default=str(ROOT / "data/actuals_all/export_manifest.json"))
    parser.add_argument("--out", default=str(ROOT / "artifacts/paper_v3_verified"))
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be between 1 and 6")
    manifest_path, out = Path(args.manifest), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "run_log_heldout.csv"
    logs = pd.read_csv(log_path).to_dict("records") if log_path.exists() else []
    submitted = {row["stock"] for row in logs}
    script_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (HERE / "paper_experiments.py", HERE / "pattern_rules.py", Path(__file__))}
    (out / "heldout_execution_manifest.json").write_text(json.dumps({
        "started_at": datetime.now(timezone.utc).isoformat(), "script_sha256": script_hashes,
        "workers": args.workers, "development_excluded": ["JKH", "BIL"],
        "design": "All available exports, unchanged eligibility and statistics.",
    }, indent=2))
    futures = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        while True:
            manifest = None
            try:
                manifest = json.loads(manifest_path.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            if manifest:
                for row in manifest["results"]:
                    if row["status"] != "exported":
                        continue
                    code = row["symbol"].replace(".", "_")
                    if code.split("_")[0] in {"JKH", "BIL"} or code in submitted:
                        continue
                    path = manifest_path.parent / row["file"]
                    if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                        raise ValueError("History fingerprint does not match export manifest.")
                    submitted.add(code)
                    futures[pool.submit(evaluate, code, str(path), str(out))] = code
            for future in list(futures):
                if future.done():
                    code = futures.pop(future)
                    try:
                        result = future.result()
                    except Exception as error:
                        result = {"stock": code, "status": "failed", "reason": repr(error)[:500]}
                    logs.append(result)
                    temporary = log_path.with_suffix(".pending")
                    pd.DataFrame(logs).to_csv(temporary, index=False)
                    temporary.replace(log_path)
                    print(f"{code}: {result['status']} ({len(logs)} finished)", flush=True)
            if manifest and len({row["symbol"] for row in manifest["results"]}) >= manifest["listings"] and not futures:
                break
            time.sleep(5)
    print("Held-out queue completed.", flush=True)


if __name__ == "__main__":
    main()
