from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from component1_research import (
    FORMULA_TEXT,
    add_anomaly_columns,
    build_data_audit,
    build_data_quality_summary,
    engineer_features,
    load_stock_history,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "component1"


def _load_dashboard(stock_code: str) -> dict[str, object]:
    path = ARTIFACT_DIR / f"{stock_code.lower()}_dashboard_output.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_test_results(stock_code: str) -> pd.DataFrame:
    return pd.read_csv(ARTIFACT_DIR / f"{stock_code.lower()}_test_results.csv")


def _load_anomaly_comparison(stock_code: str) -> pd.DataFrame:
    return pd.read_csv(ARTIFACT_DIR / f"{stock_code.lower()}_anomaly_comparison.csv")


def _load_split_metrics(stock_code: str) -> pd.DataFrame:
    return pd.read_csv(ARTIFACT_DIR / f"{stock_code.lower()}_anomaly_method_split_metrics.csv")


def test_formula_direction_uses_deviation_over_scaled_volume() -> None:
    frame = pd.DataFrame(
        [
            {
                "predicted_price": 100.0,
                "actual_price": 103.0,
                "volume": 2_000_000,
                "sma_20": 100.0,
                "sma_50": 100.0,
                "ema_12": 100.0,
            }
        ]
    )
    result = add_anomaly_columns(frame, volume_scale=1_000_000.0, epsilon=1e-6)
    score = float(result.loc[0, "liquidity_aware_anomaly_score"])
    expected = 3.0 / (2.0 + 1e-6)
    inverted = (2.0 + 1e-6) / 3.0

    assert math.isclose(score, expected, rel_tol=1e-9)
    assert not math.isclose(score, inverted, rel_tol=1e-9)


def test_data_audit_marks_required_raw_fields_available() -> None:
    raw_jkh = load_stock_history("JKH")
    audit_df = build_data_audit(raw_jkh)
    available = set(audit_df.loc[audit_df["status"] == "available_raw", "field"])
    assert {"date", "open", "high", "low", "close", "volume"}.issubset(available)


def test_data_quality_summary_reports_source_and_counts() -> None:
    raw_jkh = load_stock_history("JKH")
    quality_df = build_data_quality_summary(raw_jkh)
    row = quality_df.iloc[0]

    assert row["stock"] == "JKH"
    assert int(row["rows"]) > 3000
    assert int(row["duplicate_date_count"]) == 0
    assert str(row["data_source"]) == "tradingview_cselk_fallback"


def test_feature_engineering_creates_required_columns() -> None:
    raw_jkh = load_stock_history("JKH")
    features = engineer_features(raw_jkh)
    expected_columns = {
        "return_1d",
        "log_return_1d",
        "moving_average_gap",
        "volatility_20",
        "momentum_10",
        "atr_14",
        "rsi_14",
        "volume_ratio_20d",
        "proxy_anomaly_label",
    }
    assert expected_columns.issubset(set(features.columns))


def test_saved_dashboard_schema_contains_submission_fields() -> None:
    for stock_code in ("JKH", "BIL"):
        dashboard = _load_dashboard(stock_code)
        required_dashboard_keys = {
            "analysis_date",
            "formula",
            "volume",
            "volume_scaled",
            "epsilon",
            "anomaly_threshold",
            "prediction_band_threshold",
            "threshold_basis",
            "anomaly_threshold_basis",
            "market_confirmed_score",
            "data_source_note",
            "prediction_metrics",
            "naive_baseline_metrics",
            "lstm_vs_naive_comparison",
            "directional_metrics",
            "anomaly_comparison",
            "best_anomaly_method",
            "anomaly_method_split_metrics_summary",
            "support_warning",
            "selective_direction_signal",
            "selective_direction_confidence",
            "selective_direction_threshold",
            "selective_direction_metrics",
            "signal_coverage_rate",
            "no_signal_rate",
            "shap_backend",
            "shap_explanation_target",
            "shap_explanation_note",
            "top_feature_contribution_percentage",
            "esi_latest",
            "esi_mean",
            "esi_min",
            "esi_max",
            "number_of_windows_used",
            "esi_interpretation",
            "explanation_stability_comment",
            "final_anomaly_detected",
            "liquidity_anomaly_flag",
            "prediction_band_anomaly_flag",
            "structural_value_signal",
            "thin_trading_diagnostics",
            "proxy_anomaly_label_construction",
            "forecast_basis",
            "forecast_3m",
            "forecast_reliability_metrics",
            "forecast_reliability_score",
            "forecast_reliability_interpretation",
            "direction_signal",
            "structural_forecast_3m",
            "anomaly_adjusted_forecast_3m",
            "current_price",
            "recovery_gap",
            "recovery_gap_pct",
            "target_price",
            "target_breakout_probability",
            "anomaly_adjusted_breakout_probability",
            "target_breakout_interpretation",
            "anomaly_pressure_score",
            "anomaly_pressure_threshold",
            "anomaly_pressure_threshold_basis",
            "temporary_anomaly_drag_flag",
            "anomaly_penalty_pct",
            "anomaly_type",
            "shock_adjusted_explanation",
            "external_data_limitations",
            "counterfactual_structural_forecast_3m",
            "current_regime_forecast_3m",
            "structural_suppression_gap",
            "structural_suppression_gap_pct",
            "pre_shock_anchor_price",
            "pre_shock_anchor_date",
            "regime_shift_score",
            "regime_shift_flag",
            "regime_shift_threshold",
            "regime_shift_threshold_basis",
            "suppression_materiality_threshold_pct",
            "suppressed_but_not_currently_anomalous_flag",
            "structural_suppression_interpretation",
            "counterfactual_layer_limitations",
            "novelty_statement",
            "simple_explanation",
        }
        assert required_dashboard_keys.issubset(set(dashboard))
        assert dashboard["forecast_3m"]["forecast_basis"] == "anomaly_adjusted_structural_reversion_scenario"
        assert "lower_95" in dashboard["forecast_3m"]
        assert "upper_95" in dashboard["forecast_3m"]
        assert isinstance(dashboard["anomaly_comparison"], list)
        assert isinstance(dashboard["anomaly_method_split_metrics_summary"], list)
        assert "method_text" in dashboard["best_anomaly_method"]
        assert "support_positive" in dashboard["best_anomaly_method"]
        assert dashboard["selective_direction_metrics"]["selection_split"] == "validation"
        assert dashboard["selective_direction_metrics"]["selected_threshold_basis"] == "validation_macro_f1_with_coverage_floor"
        assert dashboard["shap_explanation_note"] == "SHAP explains the surrogate anomaly-score model, not the LSTM internals directly."
        assert "zero_volume_count" in dashboard["thin_trading_diagnostics"]
        assert "zero_volume_formula_validation_pass" in dashboard["thin_trading_diagnostics"]
        assert 0.0 <= float(dashboard["target_breakout_probability"]) <= 1.0
        assert 0.0 <= float(dashboard["anomaly_adjusted_breakout_probability"]) <= 1.0
        assert isinstance(dashboard["temporary_anomaly_drag_flag"], bool)
        assert 0.0 <= float(dashboard["anomaly_penalty_pct"]) <= 0.15
        assert dashboard["anomaly_type"] in {
            "Normal movement",
            "Temporary anomaly-driven price suppression",
            "Low-liquidity anomaly",
            "Price deviation anomaly",
        }
        assert isinstance(dashboard["regime_shift_flag"], bool)
        assert isinstance(dashboard["suppressed_but_not_currently_anomalous_flag"], bool)
        assert dashboard["counterfactual_layer_limitations"]


def test_support_counts_exist_in_anomaly_metric_tables() -> None:
    expected_cols = {
        "support_positive",
        "support_negative",
        "predicted_positive_count",
        "predicted_positive_rate",
        "tn",
        "fp",
        "fn",
        "tp",
    }
    for stock_code in ("JKH", "BIL"):
        comparison = _load_anomaly_comparison(stock_code)
        split_metrics = _load_split_metrics(stock_code)
        assert expected_cols.issubset(set(comparison.columns))
        assert expected_cols.issubset(set(split_metrics.columns))
        assert set(comparison["method"]) == {
            "Z-score baseline",
            "Isolation Forest",
            "LSTM deviation method",
        }


def test_anomaly_flags_are_separate_from_value_opportunity_signal() -> None:
    frame = pd.DataFrame(
        [
            {
                "predicted_price": 100.0,
                "actual_price": 96.0,
                "volume": 10_000_000,
                "sma_20": 110.0,
                "sma_50": 110.0,
                "ema_12": 110.0,
            }
        ]
    )
    result = add_anomaly_columns(
        frame,
        volume_scale=1_000_000.0,
        epsilon=1e-6,
        downside_band=20.0,
        upside_band=20.0,
        structural_gap_threshold_pct=0.05,
        liquidity_threshold=1.0,
        prediction_band_threshold=10.0,
    )

    assert bool(result.loc[0, "structural_value_signal"]) is True
    assert bool(result.loc[0, "liquidity_anomaly_flag"]) is False
    assert bool(result.loc[0, "prediction_band_anomaly_flag"]) is False
    assert bool(result.loc[0, "final_anomaly_detected"]) is False


def test_saved_dashboard_formula_text_is_not_inverted() -> None:
    for stock_code in ("JKH", "BIL"):
        dashboard = _load_dashboard(stock_code)
        assert dashboard["formula"] == FORMULA_TEXT
        assert "deviation / (volume_scaled + epsilon)" in dashboard["formula"]
        assert "(volume_scaled + epsilon) / deviation" not in dashboard["formula"]


def test_saved_test_result_scores_match_formula_for_every_row() -> None:
    tolerance = 1e-9

    for stock_code in ("JKH", "BIL"):
        dashboard = _load_dashboard(stock_code)
        epsilon = float(dashboard["epsilon"])
        test_df = _load_test_results(stock_code)
        expected = test_df["deviation"].astype(float) / (test_df["volume_scaled"].astype(float) + epsilon)
        diff = (test_df["liquidity_aware_anomaly_score"].astype(float) - expected).abs()
        assert float(diff.max()) < tolerance, f"{stock_code} max formula diff was {float(diff.max())}"

    bil_df = _load_test_results("BIL")
    bil_zero_rows = bil_df[bil_df["volume_scaled"].astype(float) == 0.0].copy()
    assert len(bil_zero_rows) == 1
    assert str(bil_zero_rows.iloc[0]["date"]) == "2026-01-07"
    bil_dashboard = _load_dashboard("BIL")
    bil_expected = float(bil_zero_rows.iloc[0]["deviation"]) / float(bil_dashboard["epsilon"])
    assert math.isclose(
        float(bil_zero_rows.iloc[0]["liquidity_aware_anomaly_score"]),
        bil_expected,
        rel_tol=0.0,
        abs_tol=tolerance,
    )


def test_no_local_absolute_paths_in_notebooks_or_dashboards() -> None:
    banned = "/Users/hasanthasamarathunga/Desktop/Component 1"
    files_to_scan = [
        ROOT / "component1_jkh_research.ipynb",
        ROOT / "component1_bil_research.ipynb",
        ARTIFACT_DIR / "jkh_dashboard_output.json",
        ARTIFACT_DIR / "bil_dashboard_output.json",
    ]
    for path in files_to_scan:
        text = path.read_text(encoding="utf-8")
        assert banned not in text


def test_final_viva_summary_exists_and_contains_core_sections() -> None:
    path = ARTIFACT_DIR / "final_viva_summary.md"
    text = path.read_text(encoding="utf-8")
    assert path.exists()
    assert "What The Component Does" in text
    assert "Why LSTM Is Used" in text
    assert "Why A Liquidity-Aware Anomaly Score Is Needed For CSE" in text
    assert "Why SHAP Is Used" in text
    assert "What ESI Measures" in text
    assert "Counterfactual Structural Suppression Layer" in text
    assert "What The Model Can And Cannot Claim" in text
    assert "Why The Novelty Is Valid" in text


def test_selective_direction_threshold_is_selected_from_validation_only() -> None:
    for stock_code in ("JKH", "BIL"):
        dashboard = _load_dashboard(stock_code)
        selective = dashboard["selective_direction_metrics"]
        selected_threshold = float(dashboard["selective_direction_threshold"])
        coverage_floor = float(selective["coverage_floor"])
        validation_table = pd.DataFrame(selective["validation_threshold_table"])
        assert selective["selection_split"] == "validation"
        assert len(validation_table) == 4

        eligible = validation_table[validation_table["signal_coverage_rate"].astype(float) >= coverage_floor].copy()
        ranked_source = eligible if not eligible.empty else validation_table
        ranked = ranked_source.sort_values(
            ["signal_macro_f1", "signal_balanced_accuracy", "signal_accuracy", "signal_coverage_rate"],
            ascending=[False, False, False, False],
        ).reset_index(drop=True)
        expected_threshold = float(ranked.iloc[0]["threshold"])

        assert math.isclose(selected_threshold, expected_threshold, rel_tol=0.0, abs_tol=1e-12)
        assert math.isclose(
            float(selective["selected_validation_metrics"]["threshold"]),
            selected_threshold,
            rel_tol=0.0,
            abs_tol=1e-12,
        )


def test_shock_adjusted_layer_values_are_consistent() -> None:
    for stock_code in ("JKH", "BIL"):
        dashboard = _load_dashboard(stock_code)
        current_price = float(dashboard["current_price"])
        structural_forecast = float(dashboard["structural_forecast_3m"])
        recovery_gap = float(dashboard["recovery_gap"])
        recovery_gap_pct = float(dashboard["recovery_gap_pct"])

        assert math.isclose(recovery_gap, structural_forecast - current_price, rel_tol=0.0, abs_tol=1e-6)
        assert math.isclose(recovery_gap_pct, recovery_gap / current_price, rel_tol=0.0, abs_tol=1e-6)
        assert dashboard["external_data_limitations"]


def test_anomaly_pressure_threshold_basis_is_validation_safe() -> None:
    for stock_code in ("JKH", "BIL"):
        dashboard = _load_dashboard(stock_code)
        basis = str(dashboard["anomaly_pressure_threshold_basis"]).lower()
        assert "train/validation" in basis or "train and validation" in basis
        assert "no test rows" in basis or "not use test" in basis


def test_counterfactual_structural_suppression_layer_values_are_consistent() -> None:
    for stock_code in ("JKH", "BIL"):
        dashboard = _load_dashboard(stock_code)
        current_price = float(dashboard["current_price"])
        counterfactual_forecast = float(dashboard["counterfactual_structural_forecast_3m"])
        gap = float(dashboard["structural_suppression_gap"])
        gap_pct = float(dashboard["structural_suppression_gap_pct"])

        assert math.isclose(gap, counterfactual_forecast - current_price, rel_tol=0.0, abs_tol=1e-6)
        assert math.isclose(gap_pct, gap / current_price, rel_tol=0.0, abs_tol=1e-6)
        assert isinstance(dashboard["regime_shift_flag"], bool)
        assert isinstance(dashboard["suppressed_but_not_currently_anomalous_flag"], bool)
        assert dashboard["anomaly_detected"] == dashboard["final_anomaly_detected"]
        assert dashboard["counterfactual_layer_limitations"]

        basis = str(dashboard["regime_shift_threshold_basis"]).lower()
        assert "train/validation" in basis or "train and validation" in basis
        assert "historical rolling windows" in basis
        assert "no future rows" in basis

        if dashboard["suppressed_but_not_currently_anomalous_flag"]:
            assert dashboard["final_anomaly_detected"] is False
            assert dashboard["regime_shift_flag"] is True
