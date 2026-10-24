# Component 1 Research Releases

- `Component1_V3_Completed_Results_R26-IT-076.zip`: completed aggregate tables,
  per-security summary metrics, exact failure reasons, source manifest and logs.
- `Component1_Research_Code_and_Results_R26-IT-076.zip`: the same evidence plus
  current research source and the blank, unexecuted participant-study kit.
- `SHA256SUMS`: fingerprints for both archives.

These are curated current releases, not a copy of the incoming ZIP's superseded
results. Raw vendor OHLCV histories, credentials, participant records and model
weights are excluded. Rebuild with
`python3 research/component1/experiments/publish_v3_evidence.py` after the
completed-results package exists under `output/`.

The code freeze used for held-out training is commit `0ae9f9b`; execution
orchestration was preserved in `0965ec9`. Later packaging/reporting changes do
not change the models or thresholds used for that run.

This repository identifies the authors. Do not include its URL in a double-blind
review PDF unless the selected conference explicitly permits identifying links.
