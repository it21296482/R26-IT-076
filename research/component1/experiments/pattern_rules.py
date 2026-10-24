"""Deviation-pattern labelling with rules frozen on pre-2019 data.

Design
------
Every rule compares a window statistic with the distribution of that statistic
over *all windows of the same length* inside the calibration period
(2016-01-01 to 2018-12-31). Only the quantile LEVELS below are design choices;
the threshold VALUES are estimated per stock from calibration data alone, so no
2019+ observation influences any label.

FROZEN_RULES must not be edited after the multi-stock run starts. Its SHA-256
is written next to every result so later changes are detectable.

Statistics for a window W of length L (relative residual r_t, robust z_t, CUSUM C+/C-)
    cum      = prod(1 + r_t) - 1                    (cumulative deviation, reported)
    zsum     = sum(z_t) / sqrt(L)                   (volatility-normalised drift, signed)
    open     = share of sessions with C+ > 0 or C- > 0
    scale    = MAD(r in W) / MAD(r in the 252 sessions before W)
    conc     = max|r_t| / sum|r_t|                  (shock concentration)
    maxz     = max|z_t|

Labels (several may apply)
    shock-dominated       conc > Q_conc  and maxz > Q_maxz
    persistent drift down zsum < Q_low(zsum)   and open >= Q_open
    persistent drift up   zsum > Q_high(zsum)  and open >= Q_open

Revision history (development stocks JKH, BIL only; frozen before any other stock)
    1.0  drift used |cum| with one two-sided quantile. On BIL the 2017 rally (+140%)
         set the downward threshold at 314%, so drift labels were impossible.
    1.1  drift uses the signed, volatility-normalised zsum with one-sided quantiles.
    1.2  open-share test uses >= (for short windows the calibration quantile is 1.0,
         so a strict > made the drift label unreachable). FROZEN from this version.
    volatility burst      scale > Q_scale
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

FROZEN_RULES = {
    "version": "1.2",
    "calibration_start": "2016-01-01",
    "calibration_end": "2018-12-31",
    "quantiles": {"zsum_low": 0.05, "zsum_high": 0.95, "open": 0.75, "scale": 0.95, "conc": 0.95, "maxz": 0.95},
    "min_prior_sessions_for_scale": 60,
    "calibration_step": "max(1, L // 10)",
    "null_window_lengths": [20, 60],
}
RULES_SHA256 = hashlib.sha256(json.dumps(FROZEN_RULES, sort_keys=True).encode()).hexdigest()


def _mad(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return float("nan")
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def window_stats(wf: pd.DataFrame, i0: int, i1: int) -> dict | None:
    """Statistics for rows i0..i1-1 of a walk-forward residual frame (sorted by date)."""
    w = wf.iloc[i0:i1]
    prior = wf.iloc[max(0, i0 - 252):i0]
    if len(w) == 0 or len(prior) < FROZEN_RULES["min_prior_sessions_for_scale"]:
        return None
    r = w["rel_resid"].to_numpy(float)
    abs_r = np.abs(r)
    mad_in, mad_pre = _mad(r), _mad(prior["rel_resid"].to_numpy(float))
    # Tick-constrained stocks: fall back to mean absolute deviation when MAD is 0.
    if not mad_pre or not np.isfinite(mad_pre):
        mad_pre = float(np.mean(np.abs(prior["rel_resid"] - prior["rel_resid"].mean())) * 1.2533)
    if not mad_in or not np.isfinite(mad_in):
        mad_in = float(np.mean(np.abs(r - r.mean())) * 1.2533)
    z = w["rz"].to_numpy(float)
    z = z[np.isfinite(z)]
    return {
        "cum": float(np.prod(1 + r) - 1),
        "zsum": float(z.sum() / np.sqrt(len(z))) if len(z) else 0.0,
        "open": float(((w["cusum_plus"] > 0) | (w["cusum_minus"] > 0)).mean()),
        "scale": float(mad_in / mad_pre) if mad_pre > 0 else float("nan"),
        "conc": float(abs_r.max() / abs_r.sum()) if abs_r.sum() > 0 else 0.0,
        "maxz": float(np.nanmax(np.abs(w["rz"].to_numpy(float)))) if w["rz"].notna().any() else 0.0,
        "neg_share": float((r < 0).mean()),
    }


def calibrate(wf: pd.DataFrame, length: int) -> dict:
    """Length-matched thresholds from calibration-period windows only."""
    d = wf["date"]
    cal = np.where((d >= FROZEN_RULES["calibration_start"]) & (d <= FROZEN_RULES["calibration_end"]))[0]
    if len(cal) < length + 1:
        raise ValueError(f"Calibration period too short for window length {length}")
    step = max(1, length // 10)
    rows = []
    for i0 in range(cal[0], cal[-1] - length + 2, step):
        s = window_stats(wf, i0, i0 + length)
        if s is not None:
            rows.append(s)
    if len(rows) < 20:
        raise ValueError(f"Only {len(rows)} calibration windows for length {length}")
    c = pd.DataFrame(rows)
    q = FROZEN_RULES["quantiles"]
    return {
        "length": length, "calibration_windows": len(c),
        "zsum_low": float(c["zsum"].quantile(q["zsum_low"])),
        "zsum_high": float(c["zsum"].quantile(q["zsum_high"])),
        "open": float(c["open"].quantile(q["open"])),
        "scale": float(c["scale"].quantile(q["scale"])),
        "conc": float(c["conc"].quantile(q["conc"])),
        "maxz": float(c["maxz"].quantile(q["maxz"])),
    }


def label(stats: dict, thr: dict) -> list[str]:
    out = []
    if stats["conc"] > thr["conc"] and stats["maxz"] > thr["maxz"]:
        out.append("shock-dominated")
    if stats["open"] >= thr["open"] and stats["zsum"] < thr["zsum_low"]:
        out.append("persistent drift down")
    if stats["open"] >= thr["open"] and stats["zsum"] > thr["zsum_high"]:
        out.append("persistent drift up")
    if stats["scale"] > thr["scale"]:
        out.append("volatility burst")
    return out


def profile_window(code: str, wf: pd.DataFrame, start: str, end: str, name: str,
                   cache: dict[int, dict]) -> dict:
    wf = wf.sort_values("date").reset_index(drop=True)
    idx = np.where((wf["date"] >= start) & (wf["date"] <= end))[0]
    if len(idx) == 0:
        return {"stock": code, "window": name, "trading_days": 0, "pattern": "no data"}
    L = len(idx)
    if L not in cache:
        cache[L] = calibrate(wf, L)
    thr = cache[L]
    s = window_stats(wf, idx[0], idx[-1] + 1)
    labels = label(s, thr) if s else []
    w = wf.iloc[idx]
    return {
        "stock": code, "window": name, "start": start, "end": end, "trading_days": L,
        "price_change_pct": float((w["actual_price"].iloc[-1] / w["prev_close"].iloc[0] - 1) * 100),
        **{f"stat_{k}": v for k, v in (s or {}).items()},
        **{f"thr_{k}": v for k, v in thr.items() if k not in ("length",)},
        "daily_alarm_days": int(w["daily_alarm"].sum()) if "daily_alarm" in w else np.nan,
        "cusum_alarm_days": int(w["cusum_alarm"].sum()) if "cusum_alarm" in w else np.nan,
        "pattern": "; ".join(labels) if labels else "none",
        "rules_sha256": RULES_SHA256,
    }


def null_rates(code: str, wf: pd.DataFrame, episodes: list[dict], eval_start: str, eval_end: str,
               cache: dict[int, dict]) -> list[dict]:
    """Label rates on non-overlapping out-of-episode windows after calibration."""
    wf = wf.sort_values("date").reset_index(drop=True)
    d = wf["date"]
    in_ep = pd.Series(False, index=wf.index)
    for e in episodes:
        in_ep |= (d >= e["start"]) & (d <= e["end"])
    out = []
    for L in FROZEN_RULES["null_window_lengths"]:
        if L not in cache:
            cache[L] = calibrate(wf, L)
        thr = cache[L]
        ev = np.where((d >= eval_start) & (d <= eval_end))[0]
        counts = {"windows": 0, "any": 0, "shock-dominated": 0, "persistent drift down": 0,
                  "persistent drift up": 0, "volatility burst": 0}
        i = ev[0] if len(ev) else len(wf)
        while i + L <= (ev[-1] + 1 if len(ev) else 0):
            if not in_ep.iloc[i:i + L].any():
                s = window_stats(wf, i, i + L)
                if s:
                    labs = label(s, thr)
                    counts["windows"] += 1
                    counts["any"] += bool(labs)
                    for lab in labs:
                        counts[lab] += 1
            i += L
        n = max(counts["windows"], 1)
        out.append({"stock": code, "window_length": L, "windows": counts["windows"],
                    **{f"rate_{k.replace(' ', '_').replace('-', '_')}": counts[k] / n
                       for k in counts if k != "windows"},
                    "rules_sha256": RULES_SHA256})
    return out


def write_frozen_config(path: Path) -> None:
    path.write_text(json.dumps({"rules": FROZEN_RULES, "sha256": RULES_SHA256}, indent=2))
