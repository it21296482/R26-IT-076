# Explainable Financial-Market Risk Impact Research

## Integrated contribution

This package preserves the member branch artifacts for provenance and adds a
reproducible CSE-specific current-risk model for the two stocks available in the
product, BIL and JKH. It runs through the existing Express workflow; it does not
start a second Flask server or create a separate investor page.

The live model combines:

- latest price and volume;
- 10-session and 50-session price references;
- recent return, drawdown, relative variability, and unusual trading activity;
- current Gold, Oil, and VIX levels and their recent changes;
- the selected stock identity.

This stage also owns the quantitative external-market context presented beside
the risk result: dated Gold, Oil, VIX, USD/LKR, and ASPI evidence. The trained
classifier uses Gold, Oil, and VIX; the additional indicators provide wider
market interpretation and are not presented as classifier inputs.

It returns LOW, MEDIUM, or HIGH current financial-market risk plus per-feature
SHAP contributions for the predicted class. This risk state is separate from
the future price paths produced by the market-forecasting research.

## Reproducible method

1. `server/scripts/exportRiskTrainingData.js` exports BIL and JKH price/volume
   history from MongoDB without credentials or user data.
2. `train_cse_risk_model.py --refresh-factors` collects dated Gold, Oil, and VIX
   histories, calculates the documented current-risk index, and assigns
   stock-specific LOW/MEDIUM/HIGH tertiles from each training period.
3. Data is split chronologically 80/20 within each stock.
4. A 300-tree Random Forest is trained on the first period and evaluated only on
   the later period.
5. A second stock-only model provides an ablation comparison for the incremental
   value of Gold, Oil, and VIX.
6. `predict_risk.py` loads the evaluated artifact and uses the correct
   instance-by-feature-by-class SHAP axis before ranking explanations.

The target index combines observable price variability, 20-session return and
drawdown, unusual volume, VIX level, and recent Gold/Oil movement. It measures a
current risk state, not a future loss.

## Evaluation

The stored chronological holdout contains 1,320 later BIL/JKH observations:

- accuracy: `0.859848`;
- balanced accuracy: `0.866837`;
- macro-F1: `0.859486`;
- majority baseline macro-F1: `0.124795`;
- stock-only ablation macro-F1: `0.828456`;
- macro-F1 improvement from global indicators: `0.031030`.

The full class report, confusion matrix, dates, target thresholds, feature
importance, and limitations are stored in
`models/cse_risk_model_metadata.json`.

## Honest scope

- The evaluated runtime scope is BIL and JKH only. An unseen stock is rejected;
  no proxy classification is invented.
- Metrics measure fidelity to the documented current-risk labels. They are not
  evidence of future-return or loss prediction.
- SHAP explains how the classifier used its inputs; it does not prove that a
  global factor caused the stock's real-world risk or price movement.
- Independent validation of the risk definition, rolling regime tests, and
  broader CSE stock coverage remain future research.

## Reproduce

```bash
cd server
npm run export:risk-data

cd ../research/component4
python -m pip install -r requirements.txt
python train_cse_risk_model.py --refresh-factors
python -m pytest -q
```
