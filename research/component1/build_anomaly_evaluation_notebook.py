"""Add reproducible anomaly evaluation cells without changing historical outputs.

Run this script, then execute the standalone notebook. Existing stock notebooks
use current in-kernel results after training, or explicitly labelled saved evidence.
"""

from pathlib import Path
import copy
import sys

import nbformat as nbf


ROOT = Path(__file__).resolve().parent
TAG = "component1-anomaly-evaluation"

INTRO = r"""## Anomaly detection: accuracy is not enough

An anomaly is an unusual movement, not automatically a good or bad investment.
We compare predicted flags with **research proxy labels**, not independently
confirmed real-world anomalies. False alarms and missed anomalies below are
relative to those proxy labels.

| Measure | Formula | Plain English |
|---|---|---|
| Accuracy | $(TP+TN)/(TP+TN+FP+FN)$ | Share of all checks classified correctly |
| Precision | $TP/(TP+FP)$ | Of the flags raised, how many matched a labelled anomaly? |
| Recall | $TP/(TP+FN)$ | Of the labelled anomalies, how many were detected? |
| F1 | $2TP/(2TP+FP+FN)$ | Balance between precision and recall |
| False alarms | $FP$ | Flagged, but the proxy label says normal |
| Missed anomalies | $FN$ | Proxy-labelled anomaly that was not flagged |

TP = correctly flagged anomaly; TN = correctly unflagged normal observation.
If a denominator is zero, the implementation reports zero for that metric.
The always-normal reference shows why high accuracy alone can hide missed rare
events. **Price forecast MAE, RMSE and MAPE are different measurements.**
In particular, `100 - MAPE` is not anomaly accuracy or a probability of success.

The cells below prefer current training results for this stock when available.
Otherwise they load the saved historical evaluation and show its dates explicitly.
They do not fetch today's prices or retrain a model by themselves.
"""

SETUP = '''from pathlib import Path
import sys
import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Markdown, display

# Find the research package from either the repository or notebook directory.
_eval_candidates = [candidate for parent in [Path.cwd(), *Path.cwd().parents]
                    for candidate in (parent, parent / "research" / "component1")]
EVAL_ROOT = next(candidate for candidate in _eval_candidates
                 if (candidate / "src" / "component1_research.py").is_file())
if str(EVAL_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(EVAL_ROOT / "src"))
from component1_research import compute_classification_metrics, compute_confusion_counts

def evaluation_binary(series):
    # Do not turn the string "False" into True by using astype(bool).
    encoded = series.astype(str).str.lower().map(
        {"true": 1, "false": 0, "1": 1, "0": 0, "1.0": 1, "0.0": 0})
    if encoded.isna().any():
        raise ValueError("Missing or invalid binary evaluation labels")
    return encoded.to_numpy(dtype=int)

def show_anomaly_evaluation(symbol, current_results=None):
    symbol = symbol.upper()
    if current_results is not None:
        test = current_results["test_results"].copy()
        comparison = current_results["anomaly_comparison"].copy()
        splits = current_results["anomaly_method_split_metrics"].copy()
        source = "Current in-kernel research run (not a saved historical result)"
        fingerprint = "See this notebook's training cells and configuration"
    else:
        folder = EVAL_ROOT / "artifacts" / "component1"
        test_path = folder / f"{symbol.lower()}_test_results.csv"
        test = pd.read_csv(test_path)
        comparison = pd.read_csv(folder / f"{symbol.lower()}_anomaly_comparison.csv")
        splits = pd.read_csv(folder / f"{symbol.lower()}_anomaly_method_split_metrics.csv")
        source = f"Saved historical evidence: {test_path.relative_to(EVAL_ROOT)}"
        fingerprint = hashlib.sha256(test_path.read_bytes()).hexdigest()

    actual = evaluation_binary(test["proxy_anomaly_label"])
    predicted = evaluation_binary(test["final_anomaly_detected"])
    metrics = compute_classification_metrics(actual, predicted)
    counts = compute_confusion_counts(actual, predicted)
    assert len(actual) > 0 and len(actual) == len(predicted)
    assert sum(counts[key] for key in ("tp", "tn", "fp", "fn")) == len(test)

    # Check the exported table against the row-level flags, not just its headline.
    stored = comparison.loc[comparison["method"] == "LSTM deviation method"]
    if len(stored) != 1:
        raise ValueError("Expected exactly one deviation-method comparison row")
    for key in ("accuracy", "precision", "recall", "f1_score"):
        assert np.isclose(float(stored.iloc[0][key]), metrics[key]), key
    for key in ("tp", "tn", "fp", "fn"):
        assert int(stored.iloc[0][key]) == counts[key], key

    dates = pd.to_datetime(test["date"], errors="raise")
    display(Markdown(f"### {symbol}: evaluation evidence"))
    display(pd.DataFrame([{
        "Source": source, "First test date": str(dates.min().date()),
        "Last test date": str(dates.max().date()), "Test observations": len(test),
        "Proxy-labelled anomalies": int(actual.sum()),
        "Proxy-labelled normal": int((actual == 0).sum()),
        "Anomaly prevalence (%)": round(100 * actual.mean(), 3),
        "Test CSV SHA-256 / run provenance": fingerprint,
    }]).T.rename(columns={0: "Value"}))

    normal_prediction = np.zeros_like(actual)
    reference = {"method": "Always normal (untrained reference)",
                 **compute_classification_metrics(actual, normal_prediction),
                 **compute_confusion_counts(actual, normal_prediction)}
    table = pd.concat([comparison, pd.DataFrame([reference])], ignore_index=True)
    def readable_table(frame):
        selected = [key for key in ("method", "split", "accuracy", "precision", "recall",
                    "f1_score", "fp", "fn", "tp", "tn", "support_positive") if key in frame]
        readable = frame[selected].copy()
        for key in ("accuracy", "precision", "recall"):
            readable[key] = (100 * readable[key]).round(2)
        readable["f1_score"] = readable["f1_score"].round(4)
        return readable.rename(columns={"method": "Method", "split": "Split",
            "accuracy": "Accuracy (%)", "precision": "Precision (%)", "recall": "Recall (%)",
            "f1_score": "F1 (0-1)", "fp": "False alarms (FP)", "fn": "Missed (FN)",
            "tp": "Detected (TP)", "tn": "Normal (TN)", "support_positive": "Labelled anomalies"})
    display(Markdown("#### Held-out test comparison"))
    display(readable_table(table))

    matrix = np.array([[counts["tn"], counts["fp"]], [counts["fn"], counts["tp"]]])
    fig, ax = plt.subplots(figsize=(6.5, 5.1), layout="constrained")
    ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(1, matrix.max()))
    descriptions = [["Correct normal (TN)", "False alarm (FP)"],
                    ["Missed anomaly (FN)", "Detected anomaly (TP)"]]
    for row in range(2):
        for col in range(2):
            ax.text(col, row, f"{matrix[row, col]}\\n{descriptions[row][col]}",
                    ha="center", va="center", fontsize=10,
                    color="white" if matrix[row, col] > matrix.max() / 2 else "#122333")
    ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Normal", "Flagged anomaly"],
           yticklabels=["Normal", "Anomaly"], xlabel="Model prediction",
           ylabel="Research proxy label",
           title=f"{symbol}: deviation-method test confusion matrix\\n"
                 f"{dates.min().date()} to {dates.max().date()}")
    figure_dir = EVAL_ROOT.parents[1] / "output" / "component1-notebook-evaluation"
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_dir / f"{symbol.lower()}_anomaly_confusion.png", dpi=160)
    plt.show()
    plt.close(fig)

    display(Markdown(f"""#### What these results mean

The deviation method detected **{counts['tp']} of {counts['support_positive']}**
proxy-labelled anomalies (recall **{metrics['recall']:.1%}**). It raised
**{counts['fp']} false alarms** and missed **{counts['fn']}** labelled anomalies.
Of all flags raised, **{metrics['precision']:.1%}** matched the proxy labels.
Its F1 score was **{metrics['f1_score']:.4f}**.

The always-normal reference achieves **{reference['accuracy']:.1%} accuracy**
but detects **zero anomalies**. This is why accuracy alone is not sufficient.
These results do not prove real-world event detection, investment returns, or
accuracy on today's market. Small positive counts make precision and recall
sensitive to even one changed observation. Baselines can outperform the deviation
method; compare their F1 and false alarms rather than claiming a universal winner.
"""))
    display(Markdown("#### Split-level audit: training, validation and test"))
    display(readable_table(splits))
    display(Markdown("Training fits the models; validation supports threshold selection. "
                     "The held-out test checks performance and must not be used to tune the threshold. "
                     "Proxy labels are not independent expert-labelled ground truth."))
    return {"stock": symbol, **metrics, **counts}
'''


def section(stock=None):
    cells = [nbf.v4.new_markdown_cell(INTRO), nbf.v4.new_code_cell(SETUP)]
    if stock:
        code = f'''# Use results from Run All when present; otherwise inspect the saved evidence.
_evaluation_results = globals().get("results")
if _evaluation_results is not None and str(globals().get("stock_code", "")).upper() != "{stock}":
    raise ValueError("The current training results belong to another stock")
anomaly_evaluation_{stock.lower()} = show_anomaly_evaluation("{stock}", _evaluation_results)
'''
        cells.append(nbf.v4.new_code_cell(code))
    else:
        for symbol in ("JKH", "BIL"):
            cells.append(nbf.v4.new_code_cell(
                f'anomaly_evaluation_{symbol.lower()} = show_anomaly_evaluation("{symbol}")'))
    for cell in cells:
        cell.metadata["tags"] = [TAG]
    return cells


def main():
    if "--execute-sections" in sys.argv:
        from nbclient import NotebookClient

        for stock in ("jkh", "bil"):
            canonical = ROOT / "notebooks" / f"component1_{stock}_research.ipynb"
            notebook = nbf.read(canonical, as_version=4)
            section_cells = [c for c in notebook.cells if TAG in c.metadata.get("tags", [])]
            temporary = nbf.v4.new_notebook(cells=copy.deepcopy(section_cells))
            temporary.metadata["kernelspec"] = {
                "display_name": "Python 3", "language": "python", "name": "python3"}
            NotebookClient(temporary, timeout=180, resources={"metadata": {"path": str(ROOT)}}).execute()
            for original, executed in zip(section_cells, temporary.cells):
                if original.cell_type == "code":
                    original.outputs = executed.outputs
                    original.execution_count = executed.execution_count
            for folder in (ROOT, ROOT / "notebooks"):
                nbf.write(notebook, folder / f"component1_{stock}_research.ipynb")
            print(f"Verified and saved {stock.upper()} evaluation section; historical training outputs preserved")
        return

    standalone = nbf.v4.new_notebook(cells=[nbf.v4.new_markdown_cell(
        "# Component 1: anomaly evaluation demonstration\n\n"
        "Run all cells to reproduce the saved JKH and BIL evaluation without retraining. "
        "These are historical research results, not a new live analysis.\n\n"
        "The stock research notebooks also include this section and use current training "
        "results if those cells have already been run."
    ), *section()])
    standalone.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbf.write(standalone, ROOT / "notebooks" / "component1_anomaly_evaluation.ipynb")
    for stock in ("JKH", "BIL"):
        for folder in (ROOT, ROOT / "notebooks"):
            path = folder / f"component1_{stock.lower()}_research.ipynb"
            notebook = nbf.read(path, as_version=4)
            notebook.cells = [c for c in notebook.cells if TAG not in c.metadata.get("tags", [])]
            # Append so original cell ordering and saved historical outputs stay intact.
            notebook.cells.extend(copy.deepcopy(section(stock)))
            nbf.validate(notebook)
            nbf.write(notebook, path)


if __name__ == "__main__":
    main()
