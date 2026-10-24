# V3 Verification and Prospective Extension Record

The supplied ZIP was preserved unchanged in commit `936ee04` before this
checkout ran held-out-stock experiments. That commit is a public code snapshot,
not an institutional ethics approval, independent data timestamp, or proof that
no earlier researcher inspected another stock.

## Corrections Before New Held-Out Evaluation

- The supplied robust scale used two rolling operations with changing centres.
  It did not calculate the MAD/mean absolute deviation of each stated window.
  Both are now computed around that window's own median/mean.
- The walk-forward export accidentally stored the last detector's EWMA alarm in
  the CUSUM column. It now exports the actual CUSUM alarm.
- The participant-analysis Holm correction now preserves sorted monotonicity
  and includes the interpretation subscore in the declared secondary family.
- Concurrent history exporters now serialize atomic manifest writes.

The pattern quantile-level dictionary remains unchanged, with SHA-256
`2d904f4adc828338278f092390f41b04da165c7924fba58ba56273cf7a879b60`.
This does not make earlier numeric thresholds/results invariant to the scale fix.
New results go to `artifacts/paper_v3_verified/`, leaving supplied
`artifacts/paper_v2/` untouched.

## Statistical and Study Boundaries

Experiment A's adaptive score-OR-band alert and Experiment B's fixed-budget
standardised-score-OR-robust-residual alert are different specifications. They
must not be presented as an identical detector under two evaluations.

The supplied return-Z/Isolation-Forest baselines in Experiment A use training
cutoffs, whereas the ablations use validation tuning. Claims that every method
was validation-tuned or that these are perfectly matched comparisons are false.

The supplied binomial pattern test pools different window lengths and treats
market-linked stock cases as independent. It is exploratory, not confirmatory
evidence of pattern enrichment. Cross-stock signed-rank tests also need caution
because securities share dates, companies and market-wide events.
The verified aggregate therefore omits the binomial p-value, includes only
finished stock runs, and reports missing-observation periods separately rather
than treating them as detector misses or positive pattern labels.

The 57 matched forecast dates belong to one preserved multi-step origin, not 57
independent one-day forecast origins. HAC loss-difference p-values must not be
presented as validated general superiority or as a small-sample-corrected
multi-origin Diebold-Mariano experiment.

No participant responses, approval reference, recruitment dates or signed
translation reviews were supplied. The study is a planned offline prototype
evaluation. Do not recruit before appropriate approval and translation review,
and do not turn browser smoke-test sessions into participant evidence.

The study materials are not automatically the deployed application's output.
They contain manually authored explanation paragraphs and a two-stock answer
key. Comprehension of those materials would not by itself validate the complete
MERN system, report extraction, translation model or investment decisions.
