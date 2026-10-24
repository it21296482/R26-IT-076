# Completed Component 1 Evaluation

All 200 initially eligible held-out securities were attempted: 173 completed the
full evaluation and 27 failed fixed pattern-calibration requirements. None remain
pending. JKH and BIL are the two separate development stocks. Include the failures
and exclusions when describing the final sample.

- `aggregate/`: browsable generated tables and CSV statistics.
- `run_log_heldout.csv`: all 251 exported held-out tasks, including the 51 that
  failed initial data eligibility and the 27 calibration failures.
- `failure_details.csv`: exact failure reasons for those 27 securities.
- `export_manifest.json`: all 302 source attempts, including source exclusions.
- `run_log.csv`: the two development-stock evaluations.
- [Completed results ZIP](../../releases/Component1_V3_Completed_Results_R26-IT-076.zip):
  these files plus every completed security's summary metrics under `per_stock/`.
- [Research code and results ZIP](../../releases/Component1_Research_Code_and_Results_R26-IT-076.zip):
  current research source, completed summaries and the blank participant-study kit.

`SHA256SUMS` checks the browsable files in this directory. `ARCHIVE_SHA256SUMS`
instead checks the full results ZIP after extraction, including `per_stock/`.

Paired tests are exploratory because securities share companies, trading dates
and market events. Proxy labels are not expert-verified anomaly ground truth.
Out-of-event alerts are not independently confirmed false positives. Pattern
frequencies are descriptive. No participant study is reported. Raw vendor OHLCV
histories, credentials and participant records are not included.
