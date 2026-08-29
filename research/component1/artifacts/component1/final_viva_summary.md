# Final Viva Summary

## What The Component Does

Component 1 builds an explainable and liquidity-aware market modeling pipeline for selected CSE stocks. It predicts an expected closing price with an LSTM, compares the expected value against the observed close, scales the deviation by trading activity, compares anomaly methods, explains score behaviour with SHAP, and measures explanation stability with ESI.

## Why LSTM Is Used

The LSTM is used because OHLCV market data are sequential and the expected price should be learned from temporal structure rather than from isolated rows. In this project, the LSTM is treated primarily as an expected-price baseline for anomaly scoring, not as a guaranteed trading oracle.

## Why Price Prediction And Direction Prediction Are Different

Price-level regression asks how close the expected closing price is to the realized closing price, while direction prediction asks whether the next move is up, neutral, or down. A model can have low MAPE on price levels and still have only moderate directional skill because daily returns are noisy.

## Why A Separate Direction Classifier Was Added

The project now uses a dedicated direction-classification layer instead of relying only on the LSTM close-price regressor. This improves methodological defensibility because next-day direction is evaluated as a classification problem with its own targets, metrics, and baselines.

## Why A Neutral Threshold Improves Interpretation

Very small daily price changes can be noisy and not economically meaningful. A neutral band based on rolling volatility avoids forcing every tiny move into a hard up/down label, which makes direction evaluation more interpretable and more honest.

## Why A Liquidity-Aware Anomaly Score Is Needed For CSE

CSE stocks can experience thin trading, low participation, and occasional zero-volume or low-volume days. A plain deviation can overreact to these conditions. The liquidity-aware anomaly score keeps the main formula as `deviation / (volume_scaled + epsilon)`, which highlights suspicious deviations when liquidity support is weak. A separate market-confirmed diagnostic is also reported to show when large moves happen with stronger participation.

## Why SHAP Is Used

SHAP is used to explain which engineered features drive the surrogate liquidity anomaly score. It does not explain the internal LSTM gates directly, so the project states this limitation explicitly.

## What ESI Measures

ESI measures the overlap of the top-k SHAP factors across rolling windows. High ESI means the same factors keep appearing, which supports explanation stability. However, if trading volume dominates repeatedly, ESI can be high for a volume-led reason, so the interpretation still needs caution.

## Shock-Adjusted Anomaly Interpretation Layer

This layer separates long-term structural trend from temporary anomaly effects. For example, if a stock is gradually growing and has a model-based path toward a target price, but temporary abnormal pressure pulls it down, the dashboard can classify it as temporary anomaly-driven price suppression instead of immediately treating it as company weakness.

## Counterfactual Structural Suppression Layer

This layer separates current anomaly detection from structural suppression. A stock can be non-anomalous today because it is moving normally in the current regime, while still being structurally below the earlier no-shock expected path. The added counterfactual layer captures that gap without changing the original anomaly flag.

## Why Forecast Intervals Matter More Than A Single Predicted Price

A single forecast number can hide uncertainty. The project therefore adds conformal prediction intervals and checks whether those intervals cover realized prices at the expected rate. This makes forecast reliability a backtested calibration question, not just a point-forecast question.

## What The New Forecast Reliability Score Means

The forecast reliability score combines backtested price error, interval coverage calibration, forecast bias, and fold-level stability into a 0-to-10 score. It is calculated from the data and should not be interpreted as certainty; it is a compact summary of how trustworthy the scenario forecast appears under backtesting.

## Stock-Level Results

### JKH

- Dataset coverage: 3308 rows from 2012-02-22 to 2026-05-07.
- Price-level performance: MAE 0.3268, RMSE 0.4455, MAPE 1.586%, approximate price-level accuracy 98.414%.
- Directional performance: 3-class model Previous-day direction baseline, accuracy 45.67%, balanced accuracy 37.79%, macro F1 0.3778. Selective binary signal threshold 0.55, signal accuracy 62.94%, coverage 74.77%.
- Best anomaly result: Z-score baseline is the best-performing anomaly method on the test split with F1 score 0.7500.
- Latest state: anomaly_detected=False, risk_level=Low, anomaly_score=0.016764.
- SHAP/ESI: top factors Trading Volume, 1D Return, RSI 14D; ESI latest 1.0000, mean 0.8966, interpretation highly stable.
- Forecast: start 20.7253, end 22.5275, lower_95 15.8806, upper_95 29.1745, reliability score 9.43/10 (High).
- Shock-adjusted layer: structural forecast 22.5275, anomaly-adjusted forecast 22.5275, recovery gap 1.8275, target 23.6500, structural breakout probability 37.03%, anomaly-adjusted breakout probability 37.03%, anomaly type Normal movement.
- Counterfactual layer: current-regime forecast 22.5275, counterfactual structural forecast 20.0409, suppression gap -0.6591, regime_shift_flag=False, suppressed_but_not_currently_anomalous=False.

### BIL

- Dataset coverage: 3238 rows from 2012-02-23 to 2026-05-07.
- Price-level performance: MAE 0.1616, RMSE 0.2114, MAPE 2.467%, approximate price-level accuracy 97.533%.
- Directional performance: 3-class model Gradient Boosting Classifier, accuracy 39.81%, balanced accuracy 39.54%, macro F1 0.3663. Selective binary signal threshold 0.55, signal accuracy 67.98%, coverage 80.57%.
- Best anomaly result: Z-score baseline and Isolation Forest tie by test F1, but the result is based on only 2 proxy-positive anomaly cases.
- Latest state: anomaly_detected=False, risk_level=Low, anomaly_score=0.007397.
- SHAP/ESI: top factors Trading Volume, ATR 14D, 1D Return; ESI latest 1.0000, mean 1.0000, interpretation highly stable.
- Forecast: start 6.4067, end 6.8708, lower_95 2.6831, upper_95 11.0585, reliability score 9.09/10 (High).
- Shock-adjusted layer: structural forecast 6.8708, anomaly-adjusted forecast 6.8708, recovery gap 0.4708, target 7.0000, structural breakout probability 47.59%, anomaly-adjusted breakout probability 47.59%, anomaly type Normal movement.
- Counterfactual layer: current-regime forecast 6.8708, counterfactual structural forecast 5.9291, suppression gap -0.4709, regime_shift_flag=False, suppressed_but_not_currently_anomalous=False.

## What The Results Show

The LSTM delivers low MAPE on price levels, which supports its use as an expected-price baseline. A separate direction classifier improves the methodology because it evaluates next-day movement as a classification task with a neutral band, but the project still reports the resulting directional metrics honestly instead of claiming trading-grade prediction strength. On anomaly detection, the LSTM deviation method does not currently beat the strongest baseline in test F1, so the novelty claim is not based on outperforming every baseline.

## What The Model Can And Cannot Claim

- It can claim an explainable, liquidity-aware expected-price and anomaly-analysis framework for CSE stocks.
- It can claim that direction prediction is treated separately from price-level regression and evaluated with a neutral class when appropriate.
- It can claim that forecast reliability is evaluated with backtested conformal intervals, ensemble weighting, and explicit calibration metrics.
- It can claim that shock-adjusted anomaly interpretation separates structural trend from temporary anomaly pressure when the required evidence is present in the available data.
- It can claim that counterfactual structural suppression is evaluated separately from the current anomaly flag, so a stock can be normal today while still below an earlier model-based structural path.
- It can claim that the outputs are investor-facing and traceable through SHAP and ESI.
- It cannot claim ground-truth anomaly detection superiority because the labels are proxy labels.
- It cannot claim profitable trading performance from low MAPE alone.
- It cannot claim that the forecast path is guaranteed or investment advice.
- It cannot claim that a high reliability score removes uncertainty; it only means the forecast behaved more consistently under backtesting.

## Why The Novelty Is Valid

The novelty is not simply stock price prediction. The contribution is an explainable and liquidity-aware market modeling framework for CSE stocks that combines LSTM-based expected-price modeling, deviation-based anomaly scoring adjusted by trading volume, separated anomaly/value-signal logic, SHAP-based surrogate explanation, and ESI-based explanation stability measurement. This makes the output more suitable for investor-facing interpretation in a low-liquidity emerging-market context.
