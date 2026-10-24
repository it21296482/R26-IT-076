# Component 1 paper experiments (revision 3)

All commands run on your own machine (the export needs internet access to CSE and TradingView).

## Verified completion workflow

The supplied package is preserved in commit `936ee04`. Additional scale,
CUSUM-export and analysis corrections are documented in `REVISION_RECORD.md`
and committed before this checkout's held-out run. Its results now go to
`artifacts/paper_v3_verified/`; the supplied `paper_v2/` remains unchanged.
The original commands below describe the incoming kit, not a claim that all its
statistics or participant recruitment were already completed.

The read-only all-listing source audit has been run. To resume the bounded
held-out queue from the repository root:

```bash
python3 research/component1/experiments/run_heldout_queue.py --workers 4
```

Do not start a second queue while the first is running. Completed/excluded/
failed stocks are retained in the run log. Do not launch two exporters writing
the same manifest at once.

Rebuild the evidence-checked six-page paper, or wait for the queue to finish:

```bash
python3 research/component1/experiments/complete_v3_paper.py
python3 research/component1/experiments/complete_v3_paper.py --watch
```

The source project is `output/ieee-component1-paper-v3/`. Its generated
`completion_receipt.json` explicitly states whether the full batch finished.
No participant numbers are generated. The study remains planned until genuine
approved participant evidence exists.

## Order matters (pre-registration)

1. **Commit before running anything new.** Commit `experiments/pattern_rules.py` (pattern rules v1.2, SHA-256 `2d904f4a…`), `research/user_study/` and this README, and push. The commit date shows the rules and the study plan were fixed before the held-out results and participants existed. Do not edit `FROZEN_RULES` afterwards.
2. Export histories for every CSE listing (CSV only; MongoDB is not touched):

   ```bash
   cd server
   node scripts/exportResearchHistories.js --all --until 2026-08-28
   ```

   Output: `research/component1/data/actuals_all/*.csv` plus `export_manifest.json`, which records why each listing was or was not exported (needed for the paper's inclusion counts). Re-running skips listings already exported.

3. Run the experiments on all eligible stocks (inclusion rule is fixed in `eligibility()`):

   ```bash
   cd research/component1
   python experiments/paper_experiments.py --stocks ALL --data-dir data/actuals_all --resume
   ```

   About 2–3 minutes per stock on a 2-core laptop (11 walk-forward LSTM refits each). To use more cores, run shards in separate terminals:

   ```bash
   python experiments/paper_experiments.py --stocks ALL --data-dir data/actuals_all --resume --shard 1/4
   python experiments/paper_experiments.py --stocks ALL --data-dir data/actuals_all --resume --shard 2/4
   # ... 3/4 and 4/4
   ```

   If a run stops, re-run the same command; `--resume` continues where it left off.

4. Also run the development stocks into the same folder, so that they're reported separately:

   ```bash
   python experiments/paper_experiments.py --stocks JKH BIL --resume
   ```

5. Aggregate and generate the paper tables:

   ```bash
   python experiments/aggregate_results.py
   ```

   Copy `artifacts/paper_v2/aggregate/tables_generated.tex` next to the paper's `main.tex`. Statistics are in `aggregate/*.csv` (`agg_paired_tests.csv` has the Wilcoxon tests with Holm-adjusted p).

## Experiments

| ID | What | Output (per stock in `artifacts/paper_v2/per_stock/<CODE>/`) |
|---|---|---|
| A | Daily detection on past-only labels, validation-tuned ablations, block-bootstrap F1 CIs | `exp_a_detector_ablation.csv`, `exp_a_run_metadata.csv` |
| B | Walk-forward detection of documented CSE episodes at an equal 2% alarm budget | `exp_b_episode_detection.csv`, `walk_forward_residuals.csv` |
| C | Diebold–Mariano test of preserved forecasts vs persistence (JKH/BIL only) | `exp_c_diebold_mariano.csv` |
| D | Deviation-pattern labels with rules frozen on 2016–2018, plus background rates | `exp_d_pattern_profiles.csv`, `exp_d_null_rates.csv` |
| E | Surrogate explanation fidelity (`explanation_experiment.py`, JKH/BIL) | `exp_e_explanations.csv` |

`make_paper_figure.py` draws Fig. 2. `export_mongo_history.py` is an alternative exporter if you prefer to use histories already stored in MongoDB.
