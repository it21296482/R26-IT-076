# Explainable Financial-Market Risk Impact Research

## Integrated contribution

This package preserves the supplied Random Forest classifier and stock encoder
while integrating them through the existing Express analysis workflow. It does
not start the branch's separate Flask server or add a separate investor page.

The adapter receives:

- the latest selected-stock close and volume;
- averages from the previous 10 and 50 stored sessions;
- recent price variability;
- the same latest gold, crude-oil, and VIX observations collected for the
  integrated analysis.

It returns LOW, MEDIUM, or HIGH risk plus per-feature contributions for the
predicted class. The original branch indexed the three-dimensional multiclass
explanation array on the feature axis. `predict_risk.py` corrects this by
selecting all features for the predicted class before ranking the drivers.

## Honest scope

- The supplied encoder contains three CSE stock codes: `HHL`, `JKH`, and
  `LLUB`. The current product database contains `JKH.N0000` and `BIL.N0000`.
  Therefore JKH receives this risk assessment, while BIL is explicitly marked
  unsupported instead of being mapped to another company.
- `data/final_updated_dataset.xlsx` is the supplied 33-security dataset with
  gold, oil, and VIX columns. It has no saved risk-label column.
- The branch does not include the training script, label-construction method,
  train/test split, confusion matrix, or held-out performance report. The model
  can be integrated and demonstrated, but its accuracy must not be claimed as
  validated until those artifacts are supplied or the experiment is reproduced.
- Feature contribution explains the trained classifier's output; it does not
  prove that a global factor caused the stock's real-world risk or price move.

## Runtime

The Node adapter is `server/src/services/riskImpactService.js`. It invokes:

```bash
python research/component4/predict_risk.py --input prepared-risk-input.json
```

The Python environment already used by the market research package supplies
`pandas`, `scikit-learn`, `joblib`, and `shap`.
