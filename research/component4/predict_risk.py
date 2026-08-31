"""Run the preserved financial-market risk classifier without a second web server."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "cse_risk_model.pkl"
ENCODER_PATH = ROOT / "models" / "cse_stock_encoder.pkl"
METADATA_PATH = ROOT / "models" / "cse_risk_model_metadata.json"
FEATURES = [
    "Close", "Volume", "MA10", "MA50", "Volatility", "Return20Pct",
    "Drawdown20Pct", "VolatilityPct", "VolumeRatio20", "Gold", "Oil", "VIX",
    "GoldChange30dPct", "OilChange30dPct", "VIXChange30dPct", "Stock_encoded",
]
RISK_LABELS = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
FACTOR_LABELS = {
    "Close": "Latest share price",
    "Volume": "Latest trading volume",
    "MA10": "Recent average price",
    "MA50": "Longer-term average price",
    "Volatility": "Recent price variability",
    "Return20Pct": "Recent price direction",
    "Drawdown20Pct": "Distance below the recent high",
    "VolatilityPct": "Price variability relative to the share price",
    "VolumeRatio20": "Trading activity compared with its recent norm",
    "Gold": "Gold price",
    "Oil": "Crude-oil price",
    "VIX": "Global market stress",
    "GoldChange30dPct": "Gold's recent movement",
    "OilChange30dPct": "Crude oil's recent movement",
    "VIXChange30dPct": "Change in global market stress",
    "Stock_encoded": "Stock-specific historical profile",
}
FACTOR_MEANINGS = {
    "Close": "The latest price is considered against the stock's recent and longer-term pattern.",
    "Volume": "Trading volume shows how much market participation accompanied the latest price.",
    "MA10": "The recent average helps show whether the latest price has moved away from its short-term pattern.",
    "MA50": "The longer average provides a broader reference for the stock's current position.",
    "Volatility": "Larger recent price swings generally indicate a less stable trading environment.",
    "Return20Pct": "The recent price direction shows whether the stock has been gaining or losing ground over roughly one trading month.",
    "Drawdown20Pct": "This shows how far the share currently sits below its highest level in the recent period.",
    "VolatilityPct": "This puts recent price variability in proportion to the stock's own price level.",
    "VolumeRatio20": "This compares current trading activity with the stock's normal recent participation.",
    "Gold": "Gold can reflect inflation concern and defensive global investor behaviour.",
    "Oil": "Oil can affect operating, transport, and energy costs and can also reflect global disruption.",
    "VIX": "A higher VIX normally reflects greater uncertainty in global equity markets.",
    "GoldChange30dPct": "A large recent gold move can accompany changing inflation expectations or defensive investor behaviour.",
    "OilChange30dPct": "A large recent oil move can signal changing cost pressure or global disruption.",
    "VIXChange30dPct": "A sharp VIX change shows whether global equity-market stress has recently increased or eased.",
    "Stock_encoded": "The trained model retains differences observed between the stocks represented in its research dataset.",
}


def _safe_float(value: Any) -> float:
    number = float(value)
    if not np.isfinite(number):
        raise ValueError("The risk input contains a non-finite value.")
    return number


def _driver(feature: str, impact: float) -> dict[str, Any]:
    return {
        "factor": feature,
        "label": FACTOR_LABELS[feature],
        "impact": round(float(impact), 8),
        "supports_classification": bool(impact >= 0),
        "meaning": FACTOR_MEANINGS[feature],
    }


def predict(payload: dict[str, Any]) -> dict[str, Any]:
    model = joblib.load(MODEL_PATH)
    encoder = joblib.load(ENCODER_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    stock = str(payload.get("stock") or "").upper()
    supported = {str(item) for item in encoder.classes_}
    if stock not in supported:
        supported_cse = sorted(supported)
        return {
            "status": "unavailable",
            "code": "RISK_STOCK_NOT_SUPPORTED",
            "message": (
                f"The evaluated CSE risk model was not trained for {stock}. "
                f"Its verified CSE scope is {', '.join(supported_cse)}; no proxy classification was invented."
            ),
        }

    values = [
        _safe_float(payload["close"]),
        _safe_float(payload["volume"]),
        _safe_float(payload["ma10"]),
        _safe_float(payload["ma50"]),
        _safe_float(payload["volatility"]),
        _safe_float(payload["return20_pct"]),
        _safe_float(payload["drawdown20_pct"]),
        _safe_float(payload["volatility_pct"]),
        _safe_float(payload["volume_ratio20"]),
        _safe_float(payload["gold"]),
        _safe_float(payload["oil"]),
        _safe_float(payload["vix"]),
        _safe_float(payload["gold_change30d_pct"]),
        _safe_float(payload["oil_change30d_pct"]),
        _safe_float(payload["vix_change30d_pct"]),
        int(encoder.transform([stock])[0]),
    ]
    frame = pd.DataFrame([values], columns=FEATURES)
    prediction = int(model.predict(frame)[0])
    risk_level = RISK_LABELS[prediction]
    class_index = int(np.where(model.classes_ == prediction)[0][0])
    probabilities = model.predict_proba(frame)[0]

    explanation = shap.TreeExplainer(model)(frame)
    shap_values = np.asarray(explanation.values)
    if shap_values.ndim == 3:
        impacts = shap_values[0, :, class_index]
    elif shap_values.ndim == 2:
        impacts = shap_values[0, :]
    else:
        raise ValueError(f"Unexpected explanation shape: {shap_values.shape}")
    if len(impacts) != len(FEATURES):
        raise ValueError("The explanation did not return one contribution per model input.")

    all_drivers = [_driver(feature, float(impact)) for feature, impact in zip(FEATURES, impacts)]
    all_drivers.sort(key=lambda item: abs(item["impact"]), reverse=True)
    global_drivers = [
        item for item in all_drivers
        if item["factor"] in {"Gold", "Oil", "VIX", "GoldChange30dPct", "OilChange30dPct", "VIXChange30dPct"}
    ]
    strongest = all_drivers[0]
    strongest_global = global_drivers[0]
    global_direction = "supported" if strongest_global["supports_classification"] else "partly offset"
    plain_explanation = (
        f"The combined market-risk reading is {risk_level}. "
        f"{strongest['label']} was the strongest contributor to this classification. "
        f"Among the global indicators, {strongest_global['label'].lower()} had the largest measured influence and {global_direction} this classification. "
        "This describes the current observable risk state and its main drivers; it does not predict a future loss or provide investment advice."
    )

    return {
        "status": "completed",
        "stock": stock,
        "risk_level": risk_level,
        "plain_explanation": plain_explanation,
        "top_drivers": all_drivers[:3],
        "global_drivers": global_drivers,
        "market_values": {
            "gold": values[9],
            "oil": values[10],
            "vix": values[11],
        },
        "stock_inputs": {
            "close": values[0],
            "volume": values[1],
            "ma10": values[2],
            "ma50": values[3],
            "volatility": values[4],
            "return20_pct": values[5],
            "drawdown20_pct": values[6],
            "volatility_pct": values[7],
            "volume_ratio20": values[8],
            "date": payload.get("stock_date"),
        },
        "factor_dates": payload.get("factor_dates") or {},
        "class_probabilities": {
            RISK_LABELS[int(label)]: round(float(probabilities[index]), 6)
            for index, label in enumerate(model.classes_)
        },
        "model_scope": (
            f"{metadata['model_version']}; supported CSE stock codes: "
            f"{', '.join(metadata['supported_stocks'])}. Current-risk classification, not a future-loss forecast."
        ),
        "model_validation": {
            "chronological_test_accuracy": metadata["test_metrics"]["accuracy"],
            "chronological_test_macro_f1": metadata["test_metrics"]["macro_f1"],
            "majority_baseline_macro_f1": metadata["majority_baseline_macro_f1"],
            "global_indicator_macro_f1_change": metadata["global_indicator_macro_f1_change"],
        },
        "explanation_method": "Tree-based per-feature contribution for the predicted class.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess stock risk from prepared market inputs.")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = predict(json.loads(args.input.read_text(encoding="utf-8")))
    except Exception as error:  # noqa: BLE001
        result = {"status": "failed", "code": "RISK_EXECUTION_FAILED", "message": str(error)}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
