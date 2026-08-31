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
MODEL_PATH = ROOT / "models" / "risk_model.pkl"
ENCODER_PATH = ROOT / "models" / "stock_encoder.pkl"
FEATURES = ["Close", "Volume", "MA10", "MA50", "Volatility", "Gold", "Oil", "VIX", "Stock_encoded"]
RISK_LABELS = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
FACTOR_LABELS = {
    "Close": "Latest share price",
    "Volume": "Latest trading volume",
    "MA10": "Recent average price",
    "MA50": "Longer-term average price",
    "Volatility": "Recent price variability",
    "Gold": "Gold price",
    "Oil": "Crude-oil price",
    "VIX": "Global market stress",
    "Stock_encoded": "Stock-specific historical profile",
}
FACTOR_MEANINGS = {
    "Close": "The latest price is considered against the stock's recent and longer-term pattern.",
    "Volume": "Trading volume shows how much market participation accompanied the latest price.",
    "MA10": "The recent average helps show whether the latest price has moved away from its short-term pattern.",
    "MA50": "The longer average provides a broader reference for the stock's current position.",
    "Volatility": "Larger recent price swings generally indicate a less stable trading environment.",
    "Gold": "Gold can reflect inflation concern and defensive global investor behaviour.",
    "Oil": "Oil can affect operating, transport, and energy costs and can also reflect global disruption.",
    "VIX": "A higher VIX normally reflects greater uncertainty in global equity markets.",
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
    stock = str(payload.get("stock") or "").upper()
    supported = {str(item) for item in encoder.classes_}
    if stock not in supported:
        supported_cse = sorted(item for item in supported if item in {"HHL", "JKH", "LLUB"})
        return {
            "status": "unavailable",
            "code": "RISK_STOCK_NOT_SUPPORTED",
            "message": (
                f"The supplied risk model was not trained for {stock}. "
                f"Its verified CSE scope is {', '.join(supported_cse)}; no proxy classification was invented."
            ),
        }

    values = [
        _safe_float(payload["close"]),
        _safe_float(payload["volume"]),
        _safe_float(payload["ma10"]),
        _safe_float(payload["ma50"]),
        _safe_float(payload["volatility"]),
        _safe_float(payload["gold"]),
        _safe_float(payload["oil"]),
        _safe_float(payload["vix"]),
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
    global_drivers = [item for item in all_drivers if item["factor"] in {"Gold", "Oil", "VIX"}]
    strongest = all_drivers[0]
    strongest_global = global_drivers[0]
    global_direction = "supported" if strongest_global["supports_classification"] else "partly offset"
    plain_explanation = (
        f"The combined market-risk reading is {risk_level}. "
        f"{strongest['label']} was the strongest contributor to this classification. "
        f"Among the global indicators, {strongest_global['label'].lower()} had the largest measured influence and {global_direction} this classification. "
        "This describes the model's current risk category and its main drivers; it does not predict a loss or provide investment advice."
    )

    return {
        "status": "completed",
        "stock": stock,
        "risk_level": risk_level,
        "plain_explanation": plain_explanation,
        "top_drivers": all_drivers[:3],
        "global_drivers": global_drivers,
        "market_values": {
            "gold": values[5],
            "oil": values[6],
            "vix": values[7],
        },
        "stock_inputs": {
            "close": values[0],
            "volume": values[1],
            "ma10": values[2],
            "ma50": values[3],
            "volatility": values[4],
            "date": payload.get("stock_date"),
        },
        "factor_dates": payload.get("factor_dates") or {},
        "class_probabilities": {
            RISK_LABELS[int(label)]: round(float(probabilities[index]), 6)
            for index, label in enumerate(model.classes_)
        },
        "model_scope": "Preserved trained artifact; verified CSE stock codes: HHL, JKH, and LLUB.",
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
