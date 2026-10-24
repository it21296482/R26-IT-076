"""Export stored CSE histories from the application's MongoDB for the paper experiments.

Usage (from research/component1, with the backend's MONGODB_URI exported):
    pip install pymongo
    python experiments/export_mongo_history.py --min-rows 1000 --min-recent-volume-days 200

Writes data/actuals/<CODE>_actual_through_<YYYY-MM-DD>.csv for each eligible
security and prints the --stocks list to pass to paper_experiments.py.
Eligibility mirrors the application: at least --min-rows valid sessions and
positive volume on at least --min-recent-volume-days of the last 250 sessions.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--uri", default=os.environ.get("MONGODB_URI"))
    p.add_argument("--collection", default="stocks")
    p.add_argument("--min-rows", type=int, default=1000)
    p.add_argument("--min-recent-volume-days", type=int, default=200)
    p.add_argument("--symbols", nargs="*", help="optional subset, e.g. JKH.N0000 COMB.N0000")
    args = p.parse_args()
    if not args.uri:
        raise SystemExit("Set MONGODB_URI or pass --uri")

    db = MongoClient(args.uri).get_default_database()
    coll = db[args.collection]
    symbols = args.symbols or sorted(coll.distinct("symbol"))
    out_dir = ROOT / "data" / "actuals"
    out_dir.mkdir(parents=True, exist_ok=True)
    kept = []
    for sym in symbols:
        rows = list(coll.find({"symbol": sym}, {"_id": 0, "tradeDate": 1, "open": 1, "high": 1, "low": 1,
                                                 "close": 1, "volume": 1, "source": 1}))
        if len(rows) < args.min_rows:
            continue
        df = pd.DataFrame(rows).rename(columns={"tradeDate": "date"})
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
        df = df.drop_duplicates("date", keep="last").sort_values("date")
        df = df[(df["close"] > 0) & (df["high"] >= df["low"]) & (df["volume"] >= 0)]
        if len(df) < args.min_rows or int((df["volume"].tail(250) > 0).sum()) < args.min_recent_volume_days:
            continue
        code = sym.split(".")[0].upper()
        df.insert(1, "symbol", sym)
        path = out_dir / f"{code}_actual_through_{df['date'].max().date()}.csv"
        df.to_csv(path, index=False)
        kept.append(code)
        print(f"{sym}: {len(df)} rows -> {path.name}")
    print("\nEligible:", len(kept))
    print("python experiments/paper_experiments.py --stocks " + " ".join(kept))


if __name__ == "__main__":
    main()
