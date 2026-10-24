# Component 1: Conclusion, Formulas and Research Improvement Plan

**Researcher:** S. A. H. Samarathunga | IT21296482  
**Project:** AI-Powered Stock Market Insight Generator for the Colombo Stock Exchange  
**Component:** Market Modeling and Explainable AI Insight Generation  
**Evidence reviewed:** 24 October 2026

## 1. What This Component Does

Component 1 compares a stock's observed price with a price estimated from its earlier market behaviour. It measures how far the two prices differ, considers the trading volume behind that difference, and checks whether the movement is unusual enough to flag.

It also estimates possible future price paths and shows uncertainty around them. Explanations identify which measured features influenced an approximation of the anomaly score. A stability check examines whether the same leading explanatory factors recur over time.

In plain English, it answers:

- Is today's price above or below what the recent pattern suggested?
- How large is the difference, and how much trading happened?
- Is this an unusual daily movement, a continuing pattern gap, or neither?
- What do the tested forecasting methods suggest, and how uncertain are they?
- Which measured factors influenced the score, and are those explanations stable?

It does **not** establish a stock's true value, prove that a war caused a price change, or recommend buying or selling. A stock can remain depressed for months without producing a new daily anomaly: the model may have adapted to that lower-price environment.

## 2. Conclusion in Plain English

This component makes price movements easier to inspect rather than simply drawing a forecast line. It preserves the direction and size of the price difference, checks trading participation, and separates an unusual movement from an ordinary model error. It also keeps a longer-running pattern gap separate from the daily anomaly decision.

The saved experiments show both useful detections and clear weaknesses. For John Keells Holdings, the deviation method detected eight of nine proxy-labelled unusual days, but it also raised 30 false alarms. Its recall was higher than the statistical baseline, while its precision and F1 were lower. In the preserved three-month comparison, an unchanged-price forecast was more accurate than both the ensemble and the individual recurrent forecast for both tested stocks.

Therefore, the evidence supports a transparent, inspectable decision-support workflow, but not a claim that the proposed method is the most accurate forecaster or anomaly detector. The next research priority is to reduce false alarms, evaluate persistent deviation patterns, and repeat the experiments using independently reviewed events and strictly past-only calibration.

## 3. Manuscript-Ready Conclusion

This study developed a liquidity-aware market-evidence workflow for Colombo Stock Exchange equities by combining expected-price estimation, signed and absolute deviations, a participation-adjusted anomaly score, calibrated prediction-band alerts and surrogate feature explanations. The workflow distinguishes observed daily unusualness from a persistent historical-pattern gap and from uncertain future price paths. This separation provides an auditable basis for integrating market evidence with financial-report, news and external-risk findings without treating a statistical deviation as fundamental value or a causal explanation.

Evaluation of the preserved John Keells Holdings and Browns Investments records did not establish predictive superiority. Across 57 matched dates per stock, ensemble mean absolute percentage errors were 7.07% and 15.83%, compared with 2.74% and 11.76% for unchanged-price forecasts. The John Keells deviation detector recovered eight of nine proxy anomalies but generated 30 false alarms, giving an F1 score of 0.3404 compared with 0.7500 for the statistical baseline. Explanation-factor overlap was high, although strong volume-feature dominance means that stability alone cannot establish explanation quality.

These findings identify a need for better discrimination between isolated shocks, persistent directional errors and changing market regimes. Future evaluation should freeze datasets, fitted models and thresholds before issuing forecasts, test residual-pattern monitoring against simple baselines, and use independently reviewed event labels. The present contribution is an inspectable evidence framework with explicit limitations, rather than a validated claim of superior prediction, causal attribution or investor understanding.

## 4. What the Existing Evidence Actually Shows

### 4.1 Keep the Evidence Versions Separate

| Evidence | What it supports | What it does not support |
|---|---|---|
| Archived one-step results ending 7 May 2026 | Recalculation of saved deviations, alerts, proxy-label metrics and explanations | Accuracy of all later runtime upgrades |
| Preserved three-month forecasts, 8 May to 30 July 2026 | Comparison of preserved paths with 57 matched actual observations per stock | Independently preregistered prospective performance |
| Current application source | Verification that fresh fitting, horizon selection and past-only threshold adaptation are implemented | Proof that these changes improved the archived results |

The preserved histories contain 3,308 JKH rows and 3,238 BIL rows. Their source records identify a TradingView CSELK fallback; they should not be described as an independently verified, exchange-only dataset.

The scenario records state preservation on 10 May 2026, after the first forecast target. There is no independent timestamp proving that every forecast preceded its target. Three missing target dates per stock were excluded rather than filled with invented prices. Their absence alone does not prove an exchange holiday.

### 4.2 Forecast Comparison

All errors below use the same 57 matched dates for each stock. Lower is better.

| Stock | Saved path | MAE, LKR | RMSE, LKR | MAPE |
|---|---|---:|---:|---:|
| JKH | Ensemble | 1.4157 | 1.5940 | 7.07% |
| JKH | Recurrent model | 1.1090 | 1.2599 | 5.54% |
| JKH | Unchanged-price baseline | **0.5474** | **0.6170** | **2.74%** |
| BIL | Ensemble | 0.8822 | 0.9884 | 15.83% |
| BIL | Recurrent model | 0.8565 | 0.9631 | 15.38% |
| BIL | Unchanged-price baseline | **0.6561** | **0.7276** | **11.76%** |

The saved ensemble was upward-biased. The appropriate conclusion is not that a more complex model must produce a larger price change, but that model selection and uncertainty estimates need stronger out-of-sample testing.

Interval results also need both coverage and width. JKH's nominal 80% interval covered only 22 of 57 actuals, or 38.60%, with mean width LKR 2.4809. Its nominal 95% interval covered all actuals but had mean width LKR 8.9086. BIL's corresponding coverage was 100% for both intervals, with mean widths LKR 2.5653 and LKR 5.6125. A very wide interval can have high coverage without being informative.

### 4.3 Anomaly Comparison

These are **retrospective proxy-label results**, not verified real-world event-detection rates.

| Stock | Method | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| JKH | Z-score | 6 | 1 | 3 | 637 | 85.71% | 66.67% | 0.7500 |
| JKH | Isolation Forest | 6 | 17 | 3 | 621 | 26.09% | 66.67% | 0.3750 |
| JKH | Deviation method | 8 | 30 | 1 | 608 | 21.05% | 88.89% | 0.3404 |
| BIL | Z-score | 1 | 0 | 1 | 627 | 100.00% | 50.00% | 0.6667 |
| BIL | Isolation Forest | 1 | 0 | 1 | 627 | 100.00% | 50.00% | 0.6667 |
| BIL | Deviation method | 1 | 3 | 1 | 624 | 25.00% | 50.00% | 0.3333 |

An always-normal detector would achieve 98.61% accuracy for JKH and 99.68% for BIL while detecting no anomalies. This is why accuracy alone is misleading.

**Important label limitation:** archived labels can be reproduced using full-history quantiles, which allow later observations to influence the definition of earlier labelled events. The paper discloses this retrospective leakage. The newer past-only labels require their own evaluation; their implementation does not repair the interpretation of old metrics.

## 5. Formula Reference

### 5.1 Symbols and Timing

| Symbol | Meaning |
|---|---|
| \(A_t\) | Observed closing price on trading observation \(t\), in LKR |
| \(P_t\) | Expected close for observation \(t\), estimated from earlier observations |
| \(V_t\) | Shares traded on observation \(t\) |
| \(D_t\), \(d_t\) | Signed and absolute price deviation |
| \(S_t\) | Liquidity-aware anomaly score |
| \(B_t\) | Prediction-band severity |
| \(T_S\), \(T_B\) | Calibrated score and severity thresholds |
| \(\widehat A_{o+h}\) | Forecast made at origin \(o\) for \(h\) later trading observations |
| \(Q_q\) | Quantile at proportion \(q\), estimated on the stated reference data |

An observed-day score can use that day's closing price and volume. A forecast issued before that close cannot use those unknown values. One-step expected prices and multi-month forecasts are different outputs.

### 5.2 Expected Price and Current Return-Based Learning

The archived one-step model uses 20 preceding observations:

\[
P_t=f_\theta(\mathbf{x}_{t-20},\ldots,\mathbf{x}_{t-1}).
\tag{1}
\]

The retained archived model has two recurrent layers of 32 units, dropout 0.15, batch size 32, a maximum of 12 epochs and early stopping after four non-improving validation epochs. These are archived settings, not a description of every current run.

The current return-based path learns relative price change and converts it back to price:

\[
y_t=\ln(A_t/A_{t-1}),\qquad
P_t=A_{t-1}\exp\{\operatorname{clip}(w\widehat y_t,-5,5)\}.
\tag{2}
\]

The blend \(w\in\{0,0.1,0.25,0.5,1\}\) is chosen using validation price error. If \(w=0\), the result is explicitly an unchanged-price estimate, not evidence that the network predicted growth.

Archived price-level training uses mean squared error. Current return-mode training uses the default Smooth L1 loss on the scaled target:

\[
\operatorname{MSE}=\frac1n\sum_i(\widehat y_i-y_i)^2,\qquad
\ell(e)=
\begin{cases}
0.5e^2,&|e|<1,\\
|e|-0.5,&|e|\ge1.
\end{cases}
\tag{3}
\]

Here \(e\) is error in the training target's scaled units. Current code also clips gradient norm to 1 and compares learning rates \(10^{-3}\) and \(3\times10^{-4}\) using validation price MAE.

### 5.3 Signed, Absolute and Percentage Deviation

\[
D_t=A_t-P_t,\qquad
d_t=|A_t-P_t|,\qquad
\delta_t=100\frac{A_t-P_t}{P_t},\quad P_t>0.
\tag{4}
\]

Negative \(D_t\) means below expectation; positive means above. Absolute deviation removes direction. The percentage denominator is the expected price, not the actual price.

**Illustrative example, not a current quote:** expected LKR 24.00, actual LKR 19.80:

\[
D_t=-4.20,\quad d_t=4.20,\quad \delta_t=-17.50\%.
\]

This does not prove that LKR 24.00 is fair value or that the price will recover to it.

### 5.4 Volume Scaling and Anomaly Score

\[
v_t=\frac{V_t}{1{,}000{,}000},\qquad
S_t=\frac{d_t}{v_t+\epsilon},\qquad \epsilon=10^{-6}.
\tag{5}
\]

With the example above and 2,000,000 shares:

\[
v_t=2,\qquad S_t=\frac{4.20}{2+0.000001}=2.09999895\approx2.10.
\]

For the same gap and 500,000 shares, the score is approximately 8.40. Less trading increases this score; greater trading decreases it.

The score is **not** a percentage, a probability, or a directly comparable value across all stocks. Its scale depends on price and volume units. The small epsilon prevents division by zero but does not make a zero-volume score reliable. Current logic excludes zero volume from the liquidity alert, although the separate band rule can still flag the observation.

Two related diagnostics are:

\[
u_t=\frac{V_t}{\operatorname{median}_{20}(V)},\qquad
q_t=\frac{V_t}{\operatorname{mean}_{20}(V)},\qquad
C_t=d_t\ln(1+v_t).
\tag{6}
\]

Low volume uses \(u_t<0.50\); thin trading uses \(u_t<0.25\) or zero volume. The surrogate's volume-ratio feature uses \(q_t\), not \(u_t\). \(C_t\) is a complementary participation diagnostic, not the final anomaly rule. Missing relative-volume values are conservatively flagged by the implementation.

### 5.5 Daily Prediction Bands and Final Alert

On validation residuals, let \(r_i=A_i-P_i\), \(r_i^-=\max(P_i-A_i,0)\), and \(r_i^+=\max(A_i-P_i,0)\):

\[
b_0=\max\{Q_{0.95}(|r|),\operatorname{sd}_{pop}(|r|),10^{-6}\},
\quad
b_-=\max\{Q_{0.95}(r^-),b_0\},
\quad
b_+=\max\{Q_{0.95}(r^+),b_0\}.
\tag{7}
\]

The implementation uses the population standard deviation of **absolute** residuals here.

\[
B_t=\max\left\{
\frac{\max(P_t-A_t,0)}{b_-},
\frac{\max(A_t-P_t,0)}{b_+}
\right\}.
\tag{8}
\]

\[
a_t=\mathbf1\{(S_t\ge T_S\ \land\ V_t>0)\ \lor\ (B_t\ge T_B)\}.
\tag{9}
\]

Either check can trigger the final alert. For example, a downside gap of LKR 4.20 and calibrated downside width LKR 2.00 gives \(B_t=2.10\). With severity threshold 1.05, this triggers the band alert independently of the liquidity score.

The daily residual band is **not** the same as a three- or six-month forecast interval.

### 5.6 How Threshold Selection Works

Candidate liquidity cutoffs come from training and validation score quantiles between 0.60 and 0.995. Candidate band cutoffs are at least 1.05. Each pair is evaluated on chronological validation proxy labels:

\[
\operatorname{Precision}=\frac{TP}{TP+FP},\qquad
\operatorname{Recall}=\frac{TP}{TP+FN},
\qquad
F_{0.5}=\frac{1.25\,\operatorname{Precision}\operatorname{Recall}}
{0.25\,\operatorname{Precision}+\operatorname{Recall}}.
\tag{10}
\]

The best validation \(F_{0.5}\) wins. Ties favour precision, controlled alert rates, rate consistency, accuracy and recall. The historical cutoff is therefore a selected run parameter, not a universal constant or the model's accuracy.

The archived liquidity cutoffs were approximately 0.961452 for JKH and 0.302219 for BIL, with band severity 1.05. They must not be applied indiscriminately to other stocks or assumed to describe a newly trained model.

The current adaptive path locates the selected cutoff's reference percentile, then estimates that percentile from earlier scores in a rolling 252-observation window:

\[
T_{S,t}=\max\{Q_{q_S}(S_{t-252},\ldots,S_{t-1}),10^{-6}\},
\qquad
T_{B,t}=\max\{Q_{q_B}(B_{t-252},\ldots,B_{t-1}),1.05\}.
\tag{11}
\]

Only valid nonzero-volume scores enter the liquidity quantile. At least 60 usable past scores are required; otherwise the previously calibrated cutoff is retained. Percentiles are constrained to 0.60-0.995 for liquidity and 0.95-0.995 for severity. This is past-only adaptation for the evaluation observations; it does not itself prove robustness during a crisis.

### 5.7 Proxy Labels: Historical and Current

The archived target definition can be written as:

\[
y_t^*=\mathbf1\left\{E_t\ \lor\
\left[|r_t|>Q_{0.975}(|r|)
\ \land\
(\sigma_{20,t}>Q_{0.90}(\sigma_{20})
\ \lor\ q_t>Q_{0.90}(q))\right]\right\},
\tag{12}
\]

where \(r_t=A_t/A_{t-1}-1\), \(\sigma_{20,t}\) is rolling return volatility and \(E_t\) indicates a predefined stress window.

Archived stress windows are 22 April-10 May 2019, 9 March-15 May 2020, and 1 March-31 July 2022. They are proxy labelling choices, not proof that every observation in a window was anomalous.

Archived quantiles used the full history. Current code instead uses shifted past-only rolling quantiles, with a 252-observation window and 60-observation minimum. This removes that particular future-dependent quantile construction for later evaluation observations, but the labels remain proxies rather than independently verified truth.

### 5.8 Persistent Pattern Gap and Pressure

\[
R_t=0.35\,\operatorname{SMA}_{20,t}
+0.25\,\operatorname{SMA}_{50,t}
+0.25\,\operatorname{EMA}_{12,t}+0.15P_t,
\qquad
g_t=\frac{\max(R_t-A_t,0)}{R_t}.
\tag{13}
\]

Missing averages fall back to \(P_t\). The gap cutoff uses the 90th percentile of positive training/validation gaps; if none exist, the implementation returns zero. This edge case needs care because a zero cutoff can make a non-negative gap flag uninformative.

\(R_t\) is an observed-day historical-pattern reference. It is **not fundamental fair value** or a verified price in a hypothetical peaceful world. Its flag is not included in Equation (9).

A separate pressure diagnostic is:

\[
\Pi_t=\sum_{j\in J}\left|\frac{x_{j,t}-\mu_j}{s_j}\right|,
\qquad
T_\Pi=Q_{0.90}(\Pi_{\mathrm{train+validation}}).
\tag{14}
\]

The base features are one-day return, five-day return, 20-day volatility, volume-to-mean ratio and \(S_t\). Optional external proxies enter only when present. Reference means and population standard deviations use training/validation data. A non-positive scale is replaced by 1; missing individual contributions contribute zero. Availability must therefore be disclosed: a lower pressure score is not proof that missing external conditions were harmless.

### 5.9 Current Horizon Forecasting

The current default fits separate models for \(h\in\{4,21,60,120\}\) trading observations:

\[
y_{o,h}=\ln(A_{o+h}/A_o),\qquad
\widehat A_{o+h}=A_o\exp\{\operatorname{clip}(\widehat y_{o,h},-2,2)\}.
\tag{15}
\]

Candidates are persistence, scaled ridge regression with penalties 1/10/100/1000, random forest, extra trees and histogram gradient boosting. The selection criterion is:

\[
E_h=\frac1n\sum_o
\frac{|\widehat A_{o+h}-A_{o+h}|}{A_o}.
\tag{16}
\]

The denominator is the origin price; this is not the actual-price MAPE in Equation (20). Completed targets are purged across chronological boundaries. Earlier frozen holdout evaluation and later live selection are recorded separately. Refit uses available completed outcomes; it cannot learn unknown future targets.

The chart interpolates between the trained horizon endpoints. Those intermediate points are not independently trained daily forecasts. Dates currently exclude weekends but do not implement the official CSE holiday calendar.

Calibration uses origin-normalised absolute errors \(e_{o,h}=|A_{o+h}-\widehat A_{o+h}|/A_o\). Widths combine empirical error quantiles and a recent-volatility floor:

\[
c_{0.80,h}=\max\{Q_{0.80}(e_h),1.2816\,\sigma_{recent}\sqrt h\},
\quad
c_{0.95,h}=\max\{Q_{0.95}(e_h),c_{0.80,h},1.96\,\sigma_{recent}\sqrt h\}.
\tag{17}
\]

For the horizon error quantile, sort the \(n\) calibration errors and use rank \(\min(n,\lceil(n+1)p\rceil)\), counting from one, at target coverage \(p\). This is the implementation's finite-sample rank adjustment rather than an interpolated ordinary quantile.

Successive horizon widths are made non-decreasing. With latest price \(A_o\), endpoint width is \(w_{p,h}=A_oc_{p,h}\), and displayed bounds are \(\max(0.01,\widehat A_{o+h}-w_{p,h})\) and \(\widehat A_{o+h}+w_{p,h}\). Volatility uses recent log returns. These are empirical ranges with a heuristic floor, not guaranteed coverage or event-conditioned best/worst prices.

The separate archived ensemble used validation-MAE weighting:

\[
w_i=\frac{1/\max(\operatorname{MAE}_{val,i},10^{-6})}
{\sum_j1/\max(\operatorname{MAE}_{val,j},10^{-6})},
\qquad
\widehat A_{o+h}=\sum_iw_i\widehat A^{(i)}_{o+h}.
\tag{18}
\]

Do not describe this archived ensemble as the current per-horizon selection algorithm.

### 5.10 Explanations and Explanation Stability

A random-forest surrogate estimates \(S_t\) from nine measured features. Tree SHAP decomposes the surrogate prediction:

\[
f_s(\mathbf{x}_t)=\phi_0+\sum_j\phi_{j,t},
\qquad
p_{j,t}=\frac{|\phi_{j,t}|}{\sum_k|\phi_{k,t}|}.
\tag{19}
\]

If all magnitudes are zero, their reported shares are zero. Signed contributions show direction relative to the surrogate baseline; magnitude shares do not show direction. This explains the **surrogate score model**, not the recurrent network's internal reasoning or the causal effect of news.

For each 60-observation window, advancing by 20, take the three leading factors by mean absolute attribution. Then:

\[
\operatorname{ESI}_w=\frac{|K_w\cap K_{w-1}|}{3}.
\]

Two shared factors give \(2/3=0.6667\). Mean saved ESI was 0.896552 for JKH and 1.0 for BIL. High overlap does not establish correct attribution signs, surrogate fidelity, causal validity or user comprehension.

Saved latest-observation magnitude shares assign roughly 89.79% for JKH and 97.36% for BIL to the volume-to-mean feature. These are local shares, not whole-test average importance. Dominance may partly reflect the score's own volume denominator.

### 5.11 Performance Measures

For forecast error \(e_i=\widehat A_i-A_i\):

\[
\operatorname{MAE}=\frac1n\sum_i|e_i|,
\quad
\operatorname{RMSE}=\sqrt{\frac1n\sum_ie_i^2},
\quad
\operatorname{MAPE}=\frac{100}{n}\sum_i\frac{|e_i|}{|A_i|},
\quad
\operatorname{Bias}=\frac1n\sum_ie_i.
\tag{20}
\]

Positive forecast bias means overprediction. Note the opposite sign convention from \(D_t=A_t-P_t\). MAPE needs nonzero actual prices, and \(100-\operatorname{MAPE}\) is not prediction accuracy.

\[
\operatorname{Accuracy}=\frac{TP+TN}{N},
\quad F1=\frac{2TP}{2TP+FP+FN},
\quad \operatorname{FPR}=\frac{FP}{FP+TN},
\quad \operatorname{FNR}=\frac{FN}{TP+FN}.
\tag{21}
\]

For the JKH deviation results, precision \(=8/38=21.05\%\), recall \(=8/9=88.89\%\), F1 \(=16/47=0.3404\), and false-positive rate \(=30/638=4.70\%\). Both the 30 false alarms and the false-positive rate matter. Metrics with zero denominators must be identified rather than interpreted as meaningful evidence.

\[
\operatorname{Coverage}=\frac1n\sum_i\mathbf1\{L_i\le A_i\le U_i\},
\qquad
\operatorname{MeanWidth}=\frac1n\sum_i(U_i-L_i).
\tag{22}
\]

Multiply coverage by 100 when reporting a percentage.

### 5.12 Supporting Feature Definitions

The main price/volume features are derived from the available OHLCV observations:

\[
r_{t,k}=A_t/A_{t-k}-1,\quad
\ell_t=\ln(A_t/A_{t-1}),\quad
\operatorname{SMA}_{m,t}=\frac1m\sum_{i=0}^{m-1}A_{t-i}.
\tag{23}
\]

\[
\operatorname{EMA}_{m,t}=\alpha A_t+(1-\alpha)\operatorname{EMA}_{m,t-1},
\quad\alpha=\frac2{m+1}.
\tag{24}
\]

The main research feature path uses rolling sample standard deviation for return volatility; the direct-horizon feature path uses population standard deviation of log returns. These should not be described as identical calculations.

\[
TR_t=\max\{H_t-L_t,|H_t-A_{t-1}|,|L_t-A_{t-1}|\},
\quad
ATR_{14,t}=\operatorname{mean}_{14}(TR).
\tag{25}
\]

\[
RSI_{14,t}=100-\frac{100}{1+\overline G_{14,t}/\overline L_{14,t}},
\tag{26}
\]

where \(G_t=\max(A_t-A_{t-1},0)\) and \(L_t=\max(A_{t-1}-A_t,0)\). The implementation uses simple rolling averages, not Wilder smoothing, with explicit flat/no-loss handling.

Daily range fraction is \((H_t-L_t)/A_t\), and open-to-close change is \((A_t-O_t)/O_t\). Any feature containing the current close is available only after that close; forecast inputs must respect the issue time.

## 6. What Is Distinctive, and What Is Not Yet Proven

The defensible contribution is the **combination and evaluation of liquidity-aware residual evidence, an independent band alert, persistent-pattern context and explanation-stability reporting for the studied CSE setting**.

| Related research | Relationship to this work | Defensible distinction |
|---|---|---|
| LSTM sequence learning [R1]; financial direction modelling [R2] | Established foundations | This study adds an inspectable price-residual workflow; it did not invent recurrent forecasting |
| Amihud illiquidity [R3] | Relates movement to trading participation | Our numerator is a model price residual and denominator is share volume, not absolute return divided by monetary volume |
| General anomaly detection [R4]; Isolation Forest [R5] | Established unusualness methods and comparison baselines | The proposed alert combines a volume-scaled residual with a calibrated band rule |
| SHAP and Tree SHAP [R6, R7] | Established explanation methods | We explain a surrogate anomaly-score model and separately report rolling leading-factor overlap |
| Precision-recall evaluation for imbalance [R8] | Established evaluation guidance | We expose false alarms and missed events instead of reporting only high accuracy |

These distinctions are not proof that no earlier paper uses a similar combination. A systematic, documented literature search is still needed before claiming a first-of-its-kind method. Model combination and interface integration alone do not establish scientific superiority.

Do not claim that this component has already demonstrated reliable war/disaster prediction, universally optimal models, independently validated understanding, a causal recovery price, or generalisation to every listed company.

## 7. Improvements for Unexpected Scenarios

### 7.1 Distinguish Different Deviation Patterns

The following are **proposed experiments**, not completed or validated upgrades.

| Pattern | What a single-day score may miss | Proposed next check | Safe interpretation |
|---|---|---|---|
| One-day jump or fall | A data error may look like a shock | Check source agreement, corporate actions and scale-normalised residual | An unusual observation needing verification |
| Repeated small negative deviations | Each day remains below the daily threshold | Monitor cumulative signed residuals | Sustained below-pattern behaviour |
| Alternating large deviations | Direction cancels despite rising instability | Monitor residual scale and interval coverage | Greater uncertainty, not a definite future direction |
| Long low-price period after a shock | Retraining can make the lower regime look normal | Keep slow-reference context beside fast adaptation | No fresh daily anomaly does not mean full recovery |
| Market-wide decline | A stock-only model cannot separate shared movement | Compare with a past-fitted market/sector reference | Movement associated with broad market conditions |
| Thinly traded price gap | The denominator can inflate the score | Require valid liquidity data and compare alternative score definitions | Lower confidence in the observation |
| Split, dividend or rights issue | Mechanical changes resemble anomalies | Verify and reconcile corporate actions | An adjustment, not automatically a financial shock |

For war, flooding or other disruptions, verify dated evidence and describe an association unless a suitable causal design supports more. A lower current price plus a favourable report does not identify the price that would prevail if the event ended.

### 7.2 Proposed Robust Residual Normalisation

Compare the existing score against a robust, stock-specific residual reference:

\[
m_t=\operatorname{median}(D_{t-W:t-1}),\qquad
MAD_t=\operatorname{median}(|D_{t-W:t-1}-m_t|),
\]

\[
z_t=\frac{D_t-m_t}{1.4826\,MAD_t+\epsilon_s}.
\tag{27}
\]

This measures departure from earlier residual behaviour. The scale factor is a normal-consistency convention [R14], not an assumption that stock errors are normal. Window length, a scale-appropriate floor and alert threshold must be calibrated without test outcomes. A near-zero scale should trigger a quality warning rather than an enormous unexplained score.

### 7.3 Proposed Persistent-Shift Monitoring

An exponentially weighted residual monitor can retain evidence across days:

\[
M_t=\lambda z_t+(1-\lambda)M_{t-1},\quad0<\lambda\le1.
\tag{28}
\]

A two-sided cumulative-sum monitor can detect sustained directional departures:

\[
C_t^+=\max(0,C_{t-1}^++z_t-k),\qquad
C_t^-=\max(0,C_{t-1}^- -z_t-k).
\tag{29}
\]

Initialise both at zero; compare them with a calibrated threshold \(h\). These adapt established monitoring ideas [R9, R10], not a new invention.

**Illustrative example only:** \(z=(-0.6,-0.7,-0.8,-0.7)\) and \(k=0.2\) give \(C^-=(0.4,0.9,1.5,2.0)\). Every day could escape a large single-day threshold, while the sequence indicates persistent negative error. Neither this example nor a threshold of 2 is a validated setting for our stocks.

Financial residuals are dependent and change over time. Textbook independent-process thresholds cannot simply be copied. Tune the window, \(\lambda\), \(k\) and \(h\) on earlier data, freeze them, and evaluate false alarms and detection delay on later events. Decide and disclose the reset policy after an alert.

### 7.4 Proposed Market-Adjusted Deviation

Estimate a reference relationship using only earlier observations:

\[
r_t^{stock}=\alpha+\beta r_t^{ASPI}+\eta_t,\qquad
\widehat\eta_t=r_t^{stock}-(\widehat\alpha+\widehat\beta r_t^{ASPI}).
\tag{30}
\]

This could help distinguish broad-market association from an additional stock-specific departure. Sector returns may provide a second reference. It is not proof that the index caused the movement or that the residual identifies a particular news event.

Reliable implementation needs aligned stock/index dates, verified corporate-action treatment and adequate observations. Gold, oil and global-risk attribution remain principally Component 4's responsibility; Component 1 should pass market evidence rather than duplicate or override that conclusion.

### 7.5 How to Evaluate These Improvements

| Priority | Experiment | Evidence needed before claiming improvement |
|---|---|---|
| 1 | Repair data provenance, date alignment and corporate actions | Reconciled sources, audit trail and no fabricated backfill |
| 1 | Replace future-dependent label construction | Past-only labels plus independently reviewed event labels; annotation criteria and disagreement handling |
| 1 | Repeat chronological evaluation | Frozen selection/calibration, repeated forecast origins and untouched later test periods |
| 2 | Ablate score and band rules | Compare score-only, band-only, their OR, unscaled residual and robust residual; retune each fairly on validation |
| 2 | Add residual-pattern monitoring | Compare event recall, false alerts per period, detection delay and precision against the existing method |
| 2 | Test quiet, shock and recovery regimes separately | Define regimes without test-driven selection; include enough independently reviewed events |
| 2 | Verify explanation quality | Held-out surrogate fidelity, attribution sensitivity and stability beyond factor-name overlap |
| 3 | Expand stocks and repeated fits | Per-stock/per-horizon metrics, independent data coverage and variation across planned random seeds |

Use dependence-aware uncertainty estimates, such as a justified block bootstrap, rather than treating overlapping horizon outcomes as independent. Two BIL proxy positives cannot support a strong general claim about rare-event recall.

For forecast intervals, evaluate coverage together with width and conditional errors during stressed periods. Do not force an upward central forecast simply to appear more useful when persistence wins validation.

For explanation quality, measure the surrogate's held-out MAE and \(R^2\) against the score it approximates. Compare attribution signs, magnitudes and rankings, including non-overlapping windows. High ESI caused by permanent volume dominance is not enough. A claim about improved investor understanding needs a separate, appropriately designed participant evaluation; none is established by the saved attribution plots.

### 7.6 What Is Already Implemented

Do not present these as future features that are absent from the code:

- Fresh expected-price fitting with return-based inputs, validation-selected blending, learning-rate comparison, early stopping and gradient clipping.
- Separate 4/21/60/120-observation horizon selection from a bounded candidate set, including persistence.
- Purged completed-target boundaries, separate uncertainty calibration and explicit reporting when the live selection differs from the earlier holdout winner.
- Past-only rolling anomaly-threshold adaptation and newer past-only proxy-label quantiles.
- Daily liquidity/band alerts, persistent-pattern context and a separate pressure diagnostic.

Their presence is verified in source. Improved live accuracy, robust crisis performance and reliable event causality are **not** thereby verified.

## 8. Contribution to the Integrated System

1. **Component 1:** Supplies expected versus actual price, signed/absolute deviation, liquidity-aware score, thresholds, unusual-movement status, forecast ranges and measured-feature explanations.
2. **Component 2:** Interprets the uploaded financial report and provides company-performance evidence.
3. **Component 3:** Provides relevant news and sentiment evidence.
4. **Component 4:** Provides external-market risk evidence using stock data and global indicators such as gold, oil and the volatility index.

The final explanation should connect these evidence types while preserving their boundaries. For example: company performance may be improving while the stock shows sustained below-pattern behaviour and external risks remain elevated. The price analysis cannot, by itself, say how much of the gap a particular conflict caused.

The synthesis should retain timestamps, missing-data notices and uncertainty. It must not turn a historical reference into a promised recovery price or turn association into investment advice.

## 9. Lessons From Both Supplied Example Papers

The two astronomy papers were reviewed as **writing and presentation examples**, not as evidence about stock forecasting or as text to copy.

| Example | Relevant lesson | Application to this manuscript |
|---|---|---|
| *Galaxy Morphology Classification Based on VGG19 Deep Convolutional Neural Network*, Thrinith Fernando, Samadhi Rathnayake and Kapila Dissanayaka | Explicit dataset, training settings, architecture, per-class measures, confusion matrix and error discussion | Keep dataset/split counts, model settings, per-stock confusion counts and difficult-case discussion together |
| *A Generative Adversarial Network to Upscale the Resolution of Low-Resolution Galaxy Images*, Anuththara Hettiarachchi, Samadhi Rathnayake and Kapila Dissanayaka | Explain the proposed change, give equations, compare baselines, show quantitative/qualitative evidence and state limitations | Define our score and combination precisely; compare the same observations; show actual-versus-forecast and uncertainty plots; explain failure cases |

Our six-page paper already contains six figures, four tables and thirteen references. More figures are not automatically better evidence. The strongest next addition is a properly evaluated residual-pattern/ablation experiment, not an invented performance improvement.

Do not copy the examples' prose, figures, publisher marks, performance values or conference identifiers. Their image-classification/reconstruction results do not establish the validity or novelty of a financial detector. A receiver-operating or precision-recall curve should be added only when valid continuous scores and adequate reference labels support it, not drawn from a single binary decision.

## 10. IEEE Submission Readiness

The most defensible paper focus is:

> A liquidity-aware, explainable market-evidence workflow evaluated transparently on preserved CSE records, including its forecasting failures and anomaly-detection trade-offs.

It is not:

> A universally accurate predictor that identifies the true stock price during every crisis.

### What Can Be Retained Now

- A specific problem, a bounded contribution and a clear separation between Component 1 and supporting contributions.
- Defined equations, units, data provenance, split dates and model/calibration settings.
- Actual comparisons with persistence, a statistical detector and Isolation Forest.
- Precision, recall, F1, false alarms, interval coverage and width rather than a single attractive accuracy.
- Explicit disclosure of proxy-label leakage, limited stocks/events, uncertain forecast-registration timing and missing archived fitted weights.
- The requested six-page IEEE conference layout, without shrinking standard body text or margins.

### What Still Needs Research or Author Confirmation

- Independently labelled events, fair ablation tests and repeated leakage-controlled evaluation before claiming a superior detector.
- A new frozen-model evaluation before attributing better results to current upgrades.
- Saved fitted weights, scaler states, configuration, dependency versions, data fingerprints and issue timestamps for fully reproducible forecasts.
- A documented literature search before making a first-of-its-kind novelty claim.
- Agreement from all authors on their contributions, names, order and the submitted version.
- The actual target conference's scope, page rules, anonymity rules, submission policies and PDF checks.

IEEE provides conference templates and recommends a self-contained abstract, reproducible methods, supported results and explicit limitations [R11, R12]. The six-page maximum is the requested constraint for this manuscript, **not a universal rule for all IEEE conferences**.

No formatting or wording change can guarantee acceptance. The manuscript can be improved and carefully checked, but acceptance depends on conference fit, scientific contribution, evidence and peer review. Until the major validation gaps above are addressed, describe it as a supervisor-review manuscript rather than a guaranteed publication.

## 11. Where to Demonstrate the Logic

Paths below are relative to the repository root.

| Demonstration | Implementation or evidence |
|---|---|
| Features and their timing | `research/component1/src/component1_research.py`: `engineer_features` |
| Model fitting and return blend | Same file: `train_lstm_model`, `train_selected_price_model`, `predict_lstm`; search `return_blend` and `SmoothL1Loss` |
| Deviation, score, bands and pattern gap | Same file: `add_anomaly_columns` |
| Band widths | Same file: `calibrate_prediction_bands` |
| Validation cutoff search | Same file: `calibrate_final_anomaly_logic` |
| Past-only threshold adaptation | Same file: `apply_causal_anomaly_thresholds` |
| Pressure diagnostic | Same file: `apply_anomaly_pressure_scores` |
| Surrogate explanations and stability | Same file: `compute_shap_explanations` and its stability calculations |
| Per-horizon models and fresh refits | `research/component1/src/learned_horizon.py`: `fit_direct_horizon`, `learned_horizon_forecast` |
| Horizon definitions | `research/component1/src/horizon_forecast.py`: `HORIZONS=(4,21,60,120)` |
| App-side research entry point | `research/component1/analyze_market_on_demand.py` |
| Archived detector counts and thresholds | `research/component1/artifacts/component1/*_anomaly_confusion_matrices.csv`, `*_dashboard_output.json`, `*_threshold_calibration.json` |
| Archived forecast validation | `research/component1/artifacts/validation/forecast_validation_metrics.csv`, `forecast_interval_validation.csv` |
| Presentation notebook | `research/component1/notebooks/component1_anomaly_evaluation.ipynb` |
| Six-page paper and figure reconstruction | `output/ieee-component1-paper-six-page/main.tex`, `build_figures.py`, `evidence_manifest.json` |

The archived numeric results in this document describe saved artifacts, not a new training run. Source inspection verifies implementation; it does not replace evaluation.

## 12. References and Reading

Only references directly supporting a paper claim should be included in that paper. The supplied astronomy examples are discussed separately in Section 9 as presentation examples.

- **[R1]** S. Hochreiter and J. Schmidhuber, "Long short-term memory," *Neural Computation*, vol. 9, no. 8, pp. 1735-1780, 1997. [DOI](https://doi.org/10.1162/neco.1997.9.8.1735).
- **[R2]** T. Fischer and C. Krauss, "Deep learning with long short-term memory networks for financial market predictions," *European Journal of Operational Research*, vol. 270, no. 2, pp. 654-669, 2018. [DOI](https://doi.org/10.1016/j.ejor.2017.11.054).
- **[R3]** Y. Amihud, "Illiquidity and stock returns: Cross-section and time-series effects," *Journal of Financial Markets*, vol. 5, no. 1, pp. 31-56, 2002. [DOI](https://doi.org/10.1016/S1386-4181(01)00024-6).
- **[R4]** V. Chandola, A. Banerjee and V. Kumar, "Anomaly detection: A survey," *ACM Computing Surveys*, vol. 41, no. 3, Article 15, 2009. [DOI](https://doi.org/10.1145/1541880.1541882).
- **[R5]** F. T. Liu, K. M. Ting and Z.-H. Zhou, "Isolation forest," in *Proc. IEEE International Conference on Data Mining*, pp. 413-422, 2008. [DOI](https://doi.org/10.1109/ICDM.2008.17).
- **[R6]** S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," *Advances in Neural Information Processing Systems*, vol. 30, 2017. [Primary paper](https://proceedings.neurips.cc/paper_files/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html).
- **[R7]** S. M. Lundberg et al., "From local explanations to global understanding with explainable AI for trees," *Nature Machine Intelligence*, vol. 2, pp. 56-67, 2020. [Primary paper](https://www.nature.com/articles/s42256-019-0138-9).
- **[R8]** T. Saito and M. Rehmsmeier, "The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets," *PLOS ONE*, vol. 10, no. 3, e0118432, 2015. [Primary paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).
- **[R9]** NIST/SEMATECH, "CUSUM control charts," *e-Handbook of Statistical Methods*, Section 6.3.2.3. [Official technical reference](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm).
- **[R10]** NIST/SEMATECH, "EWMA control charts," *e-Handbook of Statistical Methods*, Section 6.3.2.4. [Official technical reference](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm).
- **[R11]** IEEE Author Center, "Authoring tools and templates." [Official conference guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/).
- **[R12]** IEEE Author Center, "Structure your paper." [Official conference guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/).
- **[R13]** R. J. Hyndman and A. B. Koehler, "Another look at measures of forecast accuracy," *International Journal of Forecasting*, vol. 22, no. 4, pp. 679-688, 2006. [DOI](https://doi.org/10.1016/j.ijforecast.2006.03.001). Supports the care needed in interpreting forecast-error measures in Sections 4-5.
- **[R14]** NIST, "Median absolute deviation," *Dataplot Reference Manual*. [Official definition and normal scaling](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/mad.htm).

## Final Takeaway

The clearest research claim is that this component makes market evidence inspectable: what the model expected, how far the observation departed, how trading participation affected the score, why an alert was raised and where uncertainty remains. Its next improvement should demonstrate fewer misleading alerts and better detection of persistent shifts on independently evaluated data, rather than promise accurate prices in every possible situation.
