# Evidence-Checked V3 Manuscript

This six-page IEEE-format manuscript replaces the supplied red placeholders
with reproduced development results, source/execution status, and an explicitly
planned participant study. It is not a claim that unfinished experiments or
human research have taken place.

## Main Corrections

- Recomputed rolling MAD/MeanAD around each window's own centre. JKH robust
  residual F1 is now 0.785714 (11 true, 5 false proxy alerts), rather than the
  supplied 0.814815. BIL remains 0.400000.
- Corrected the CUSUM export, regenerated the figure, and distinguished the
  adaptive score/band detector from the fixed-budget combined detector.
- Reproduced the two-stock annual walk-forward and explanation experiments.
- Removed unsupported completed-study, causal and general-significance claims.
- Kept all-listing source inclusion separate from completed model evaluation.

`completion_receipt.json` records the exact manuscript snapshot. Source
histories and full execution files remain locally under
`research/component1/data/actuals_all/` and
`research/component1/artifacts/paper_v3_verified/`. They are excluded from Git
to avoid publishing raw vendor histories or accidental participant material.

## Rebuild

From the repository root, using the Python environment with the research
dependencies:

```bash
python3 research/component1/experiments/complete_v3_paper.py
```

To create the current snapshot and rebuild automatically after the running
held-out queue completes:

```bash
python3 research/component1/experiments/complete_v3_paper.py --watch
```

The watcher does not submit the manuscript, push commits, or generate participant
responses. It stops if compilation exceeds six pages. Keep the machine awake for
long-running research processes.

`main.tex`, `refs.bib` and all generated TeX tables are included in the source
archive. Compile with Tectonic or a normal IEEE-compatible LaTeX installation.
The original downloaded PDF and ZIPs remain unchanged.

## Research Readiness

The study protocol is available but no participant dataset, ethics reference or
native-speaker review was supplied. These cannot be inferred from a browser
smoke test or a Git commit. The model batch's status is explicit in the paper;
an in-progress snapshot is not a final all-stocks replication report.
