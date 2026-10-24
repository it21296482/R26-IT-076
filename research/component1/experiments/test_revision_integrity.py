"""Small analytical regression tests; no network or participant sessions."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paper_experiments as pe


def test_scale_centres_each_window_independently():
    values = pd.Series([1., 2., 3., 50., 4., 5., 6., 7.])
    location, scale = pe.robust_scale(values, 4, 3)
    for end in range(2, len(values)):
        window = values.iloc[max(0, end - 3):end + 1].to_numpy()
        expected = max(1.4826 * np.median(np.abs(window - np.median(window))),
                       1.2533 * np.mean(np.abs(window - window.mean())), 1e-6)
        assert np.isclose(location.iloc[end], np.median(window))
        assert np.isclose(scale.iloc[end], expected)


def test_robust_residual_never_uses_future_values():
    original = pd.Series(np.random.default_rng(7).normal(size=100))
    changed = original.copy()
    changed.iloc[80:] = 10000
    assert pe.robust_z(original, 30, 10).iloc[:80].equals(
        pe.robust_z(changed, 30, 10).iloc[:80])


def test_block_bootstrap_handles_short_samples():
    low, high = pe.block_bootstrap_ci(np.array([1, 0]), np.array([1, 0]), reps=10)
    assert 0 <= low <= high <= 1


def test_recorded_cusum_is_not_ewma():
    dates = pd.bdate_range("2015-01-01", "2026-08-28")
    r = np.random.default_rng(42).normal(0, .02, len(dates))
    r[-5:] = -.2
    frame = pd.DataFrame({"date": dates, "zero_volume_flag": False,
                          "return_1d": r, "rel_resid": r,
                          "liquidity_aware_anomaly_score": np.abs(r)})
    frame["rz"] = pe.robust_z(frame.rel_resid)
    _, output, thresholds = pe.experiment_b("TEST", frame)
    cutoff = thresholds["Pattern: two-sided CUSUM"].iloc[0]
    _, _, expected = pe.cusum(frame.rz, pe.CUSUM_K, cutoff)
    assert output.cusum_alarm.equals(expected)


def test_holm_is_monotonic_and_handles_missing_values():
    path = HERE.parents[1] / "user_study" / "analyse_study.py"
    spec = importlib.util.spec_from_file_location("study_analysis", path)
    study = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(study)
    result = study.holm_adjust([.02, .01, .015, np.nan])
    assert np.allclose(result[:3], [.03, .03, .03])
    assert np.isnan(result[3])
