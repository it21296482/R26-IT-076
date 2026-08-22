"""Streamlit dashboard for the annual report extraction component.

The UI is intentionally simple for demonstrations and viva explanations:
select/upload a PDF, run one main button, then inspect the final report,
the 10 prompt outputs, prompt scores, evidence, and export files.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# Allow `streamlit run app/streamlit_app.py` to import modules from component_2/src.
COMPONENT_ROOT = Path(__file__).resolve().parent.parent
if str(COMPONENT_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPONENT_ROOT))

from src.build_expected_outputs import main as build_expected_outputs_main
from src.config import (
    ANNUAL_REPORTS_DIR,
    DATA_DIR,
    EVALUATION_RESULTS_DIR,
    EXPECTED_OUTPUTS_DIR,
    EXTRACTED_TEXT_DIR,
    FINAL_INSIGHTS_DIR,
    PROMPT_OUTPUTS_DIR,
    ensure_directories,
)
from src.evaluate_prompts import evaluate_all_prompts
from src.expected_output_builder import build_expected_output_from_path
from src.generate_final_insight import generate_final_insight_for_pdf
from src.pdf_extractor import save_extracted_pdf
from src.run_prompt_benchmark import run_benchmark
from src.select_best_prompt import select_best_prompt
from src.utils import read_json, slugify


st.set_page_config(page_title="Annual Report Insight Extractor", layout="wide")
ensure_directories()
UI_STATE_PATH = DATA_DIR / "ui_state.json"

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.25rem; padding-bottom: 1rem; max-width: 1480px; }
    h1 { font-size: 2.15rem !important; margin-bottom: 0.15rem !important; }
    h2, h3 { margin-top: 0.5rem !important; }
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 0.75rem;
        padding: 0.65rem;
    }
    div[data-testid="stAlert"] { padding: 0.75rem 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def run_action(label: str, action) -> None:
    """Run a dashboard action and show a user-friendly success/error message."""
    with st.spinner(label):
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - Streamlit should show any pipeline error.
            st.error(f"{label} failed: {exc}")
        else:
            st.success(f"{label} completed.")


def report_paths(pdf_name: str) -> dict[str, Path]:
    """Return every artifact path created for one PDF."""
    stem = slugify(Path(pdf_name).stem)
    return {
        "stem": Path(stem),
        "extracted": EXTRACTED_TEXT_DIR / f"{stem}_pages.json",
        "expected": EXPECTED_OUTPUTS_DIR / f"{stem}_expected.json",
        "scores_csv": EVALUATION_RESULTS_DIR / f"{stem}_prompt_scores.csv",
        "scores_json": EVALUATION_RESULTS_DIR / f"{stem}_prompt_scores.json",
        "prompt_dir": PROMPT_OUTPUTS_DIR / stem,
        "final_json": FINAL_INSIGHTS_DIR / f"{stem}_final_investor_insight.json",
        "final_md": FINAL_INSIGHTS_DIR / f"{stem}_final_investor_insight.md",
    }


def read_saved_selection() -> str | None:
    """Read the last selected PDF so app restarts keep the same company."""
    if not UI_STATE_PATH.exists():
        return None
    try:
        payload = json.loads(UI_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload.get("selected_pdf")


def save_selected_pdf(pdf_name: str) -> None:
    """Persist the selected PDF outside Streamlit session state."""
    UI_STATE_PATH.write_text(json.dumps({"selected_pdf": pdf_name}, indent=2), encoding="utf-8")


def persist_selected_pdf_from_widget() -> None:
    """Save the dropdown value only when the user changes it."""
    selected_pdf = st.session_state.get("selected_pdf_widget")
    if selected_pdf:
        save_selected_pdf(selected_pdf)


def looks_like_generated_upload_name(pdf_name: str) -> bool:
    """Detect browser/system generated names like 369_1741169817422.pdf.

    These files may still be valid PDFs, but they are confusing in the viva UI,
    so the dashboard sorts them after clearer report names such as JKH_2024.pdf.
    """
    stem = Path(pdf_name).stem
    compact_stem = stem.replace("_", "")
    return compact_stem.isdigit() and len(compact_stem) >= 10


def pdf_inventory() -> pd.DataFrame:
    """List PDFs in data/annual_reports, preferring readable report names."""
    rows = []
    for path in ANNUAL_REPORTS_DIR.glob("*.pdf"):
        stat = path.stat()
        generated_name = looks_like_generated_upload_name(path.name)
        rows.append(
            {
                "PDF": path.name,
                "Size MB": round(stat.st_size / (1024 * 1024), 2),
                "Modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "Name Type": "Uploaded/generated name" if generated_name else "Readable report name",
                "_generated_name": generated_name,
                "_modified": stat.st_mtime,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["PDF", "Size MB", "Modified", "Name Type", "_generated_name", "_modified"])
    return pd.DataFrame(rows).sort_values(["_generated_name", "_modified"], ascending=[True, False]).reset_index(drop=True)


def prompt_output_files(prompt_dir: Path) -> list[Path]:
    """Return saved prompt output JSON files for the selected report."""
    return sorted(prompt_dir.glob("prompt_*.json")) if prompt_dir.exists() else []


def company_name_for_pdf(pdf_name: str) -> str | None:
    """Return the extracted company name for a PDF if an output file has it."""
    paths = report_paths(pdf_name)

    if paths["final_json"].exists():
        final_payload = read_json(paths["final_json"])
        company_name = final_payload.get("metadata", {}).get("company_name")
        if company_name:
            return company_name

    if paths["expected"].exists():
        expected_payload = read_json(paths["expected"])
        company_payload = expected_payload.get("expected_outputs", {}).get("company_name", {})
        company_name = company_payload.get("expected_value")
        if company_name:
            return company_name

    prompt_02_path = paths["prompt_dir"] / "prompt_02.json"
    if prompt_02_path.exists():
        prompt_payload = read_json(prompt_02_path)
        company_name = prompt_payload.get("parsed_json", {}).get("metadata", {}).get("company_name")
        if company_name:
            return company_name

    return None


def report_display_label(pdf_name: str) -> str:
    """Show company name first while still keeping the PDF filename visible."""
    company_name = company_name_for_pdf(pdf_name)
    if company_name:
        return f"{company_name} ({pdf_name})"
    return pdf_name


def build_selected_expected(pdf_name: str) -> None:
    """Build the source-grounded expected output for only the selected PDF."""
    paths = report_paths(pdf_name)
    if not paths["extracted"].exists():
        save_extracted_pdf(ANNUAL_REPORTS_DIR / pdf_name)
    build_expected_output_from_path(paths["extracted"])


def evaluate_and_generate_selected(pdf_name: str) -> None:
    """Score prompt outputs, select best prompt, then create the final report."""
    evaluate_all_prompts()
    select_best_prompt()
    generate_final_insight_for_pdf(Path(pdf_name).stem)


def run_selected_full_pipeline(pdf_name: str) -> None:
    """Run the full pipeline for one report.

    The benchmark step is resumable. If the 10 prompt outputs already exist,
    run_benchmark skips them and avoids repeated Azure OpenAI calls.
    """
    save_extracted_pdf(ANNUAL_REPORTS_DIR / pdf_name)
    build_selected_expected(pdf_name)
    run_benchmark(report_name=pdf_name)
    evaluate_and_generate_selected(pdf_name)


def status_text(done: bool) -> str:
    """Short status label for the top cards."""
    return "Ready" if done else "Pending"


def best_prompt_summary() -> dict:
    """Read the global best prompt summary if evaluation has selected one."""
    summary_path = EVALUATION_RESULTS_DIR / "best_prompt_summary.json"
    return read_json(summary_path) if summary_path.exists() else {}


def remove_selected_pdf(pdf_name: str) -> None:
    """Delete an unwanted PDF and its generated artifacts from the workspace."""
    paths = report_paths(pdf_name)
    candidates = [
        ANNUAL_REPORTS_DIR / pdf_name,
        paths["extracted"],
        paths["expected"],
        paths["scores_csv"],
        paths["scores_json"],
        paths["final_json"],
        paths["final_md"],
    ]
    if paths["prompt_dir"].exists():
        candidates.extend(sorted(paths["prompt_dir"].glob("prompt_*.json")))
        candidates.append(paths["prompt_dir"])

    for path in candidates:
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
        elif path.exists():
            path.unlink()


st.title("Annual Report Insight Extractor")
st.caption("Select an annual report, run extraction, then view the final answer and all 10 prompt outputs.")

with st.expander("What happens when I click Generate Insight?", expanded=False):
    st.write(
        "It runs this pipeline: extract PDF text -> build source-grounded expected output -> "
        "run 10 prompts -> score the prompts -> select one overall best prompt -> generate the final investor report."
    )
    st.write("The same overall best prompt is used for every final report. If prompt outputs already exist, the app reuses them.")

# Step 1: choose the report in a compact top panel instead of a large sidebar.
with st.container(border=True):
    choose_col, upload_col, run_col = st.columns([1.4, 1.2, 1])

    with upload_col:
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
        if uploaded_file is not None:
            destination = ANNUAL_REPORTS_DIR / uploaded_file.name
            destination.write_bytes(uploaded_file.getbuffer())
            st.session_state["selected_pdf_widget"] = uploaded_file.name
            save_selected_pdf(uploaded_file.name)
            st.success(f"Saved {uploaded_file.name}")

    available_pdf_df = pdf_inventory()
    if available_pdf_df.empty:
        st.info("Upload an annual report PDF to begin.")
        st.stop()

    available_pdfs = available_pdf_df["PDF"].tolist()
    readable_pdfs = [pdf for pdf in available_pdfs if not looks_like_generated_upload_name(pdf)]
    remembered_pdf = st.session_state.get("selected_pdf_widget") or read_saved_selection()
    if remembered_pdf and looks_like_generated_upload_name(remembered_pdf) and readable_pdfs:
        # Reset confusing generated upload names on app restart so the UI opens
        # on a clear annual report like JKH_2024.pdf instead.
        st.session_state["selected_pdf_widget"] = readable_pdfs[0]
        save_selected_pdf(readable_pdfs[0])

    default_pdf = st.session_state.get("selected_pdf_widget") or read_saved_selection() or available_pdfs[0]
    selected_index = available_pdfs.index(default_pdf) if default_pdf in available_pdfs else 0

    with choose_col:
        selected_pdf = st.selectbox(
            "1. Select company / annual report",
            available_pdfs,
            index=selected_index,
            key="selected_pdf_widget",
            format_func=report_display_label,
            on_change=persist_selected_pdf_from_widget,
        )
        st.caption(f"{len(available_pdfs)} PDFs available")
        if looks_like_generated_upload_name(selected_pdf):
            st.warning("This looks like an auto-generated upload name. Rename or remove it if it is not needed.")
        with st.expander("Manage PDFs", expanded=False):
            st.dataframe(
                available_pdf_df.drop(columns=["_generated_name", "_modified"]),
                width="stretch",
                hide_index=True,
            )
            confirm_remove = st.checkbox(f"Confirm removal of {selected_pdf}")
            if st.button("Remove selected PDF and outputs", width="stretch", disabled=not confirm_remove):
                remove_selected_pdf(selected_pdf)
                st.session_state.pop("selected_pdf_widget", None)
                if UI_STATE_PATH.exists():
                    UI_STATE_PATH.unlink()
                st.rerun()

    with run_col:
        st.write("")
        st.write("")
        if st.button("Generate Insight", type="primary", width="stretch"):
            run_action("Generating insight", lambda: run_selected_full_pipeline(selected_pdf))

paths = report_paths(selected_pdf)
prompt_files = prompt_output_files(paths["prompt_dir"])
extracted_ready = paths["extracted"].exists()
expected_ready = paths["expected"].exists()
completed_prompts = len(prompt_files)
scores_ready = paths["scores_csv"].exists()
final_ready = paths["final_md"].exists() or paths["final_json"].exists()
best_summary = best_prompt_summary()

selected_company_name = company_name_for_pdf(selected_pdf)
st.subheader(selected_company_name or selected_pdf)
if selected_company_name:
    st.caption(f"Annual report file: {selected_pdf}")
metric_cols = st.columns(5)
metric_cols[0].metric("PDF Text", status_text(extracted_ready))
metric_cols[1].metric("Expected", status_text(expected_ready))
metric_cols[2].metric("Prompt Outputs", f"{completed_prompts}/10")
metric_cols[3].metric("Scores", status_text(scores_ready))
metric_cols[4].metric("Final Report", status_text(final_ready))

if best_summary.get("best_prompt_id"):
    st.success(
        "Overall selected best prompt: "
        f"{best_summary['best_prompt_id']} - {best_summary.get('best_prompt_name', '')}. "
        "This same prompt is used for every final report."
    )

if completed_prompts == 10 and not final_ready:
    st.warning("The 10 prompt outputs already exist, but the final report has not been built yet.")
    if st.button("Build Final Report From Existing Prompt Outputs", width="stretch"):
        run_action("Building final report", lambda: evaluate_and_generate_selected(selected_pdf))

tabs = st.tabs(["Final Report", "10 Prompt Outputs", "Scores", "Evidence", "Files"])

with tabs[0]:
    if paths["final_md"].exists():
        st.markdown(paths["final_md"].read_text(encoding="utf-8"))
    elif paths["final_json"].exists():
        st.json(read_json(paths["final_json"]))
    else:
        st.info("No final report yet. Click Generate Insight or build it from existing prompt outputs.")

with tabs[1]:
    st.caption("These are the saved outputs from your 10 prompt strategies.")
    if not prompt_files:
        st.info("No prompt outputs yet. Click Generate Insight to run the 10 prompts.")
    else:
        prompt_labels = [path.stem.replace("_", " ").title() for path in prompt_files]
        default_prompt_index = 0
        if best_summary.get("best_prompt_id"):
            best_prompt_file = f"{best_summary['best_prompt_id']}.json"
            matching_indexes = [index for index, path in enumerate(prompt_files) if path.name == best_prompt_file]
            if matching_indexes:
                default_prompt_index = matching_indexes[0]
        selected_prompt_label = st.selectbox("Choose prompt output", prompt_labels, index=default_prompt_index)
        selected_prompt_path = prompt_files[prompt_labels.index(selected_prompt_label)]
        prompt_payload = read_json(selected_prompt_path)

        info_cols = st.columns(3)
        info_cols[0].metric("Prompt ID", prompt_payload.get("prompt_id", selected_prompt_path.stem))
        info_cols[1].metric("Model", prompt_payload.get("model", ""))
        info_cols[2].metric("Runtime", f"{prompt_payload.get('runtime_seconds', 0)}s")

        st.write(f"Output file: `{selected_prompt_path}`")
        if prompt_payload.get("prompt_id") == best_summary.get("best_prompt_id"):
            st.info("This is the overall selected best prompt used for final reports.")
        st.subheader("Parsed JSON Output")
        st.json(prompt_payload.get("parsed_json"))

        with st.expander("Raw model output", expanded=False):
            st.code(prompt_payload.get("full_model_output", ""), language="json")

with tabs[2]:
    if not scores_ready:
        st.info("Scores are created after evaluation.")
    else:
        if best_summary.get("best_prompt_id"):
            st.info(
                "Final report generation uses the overall best prompt, not a different prompt for each PDF: "
                f"{best_summary['best_prompt_id']} - {best_summary.get('best_prompt_name', '')}."
            )
        score_df = pd.read_csv(paths["scores_csv"])
        visible_columns = [
            "rank",
            "prompt_id",
            "prompt_name",
            "final_score",
            "coverage_score",
            "numeric_accuracy_score",
            "similarity_score",
        ]
        existing_columns = [column for column in visible_columns if column in score_df.columns]
        st.dataframe(score_df[existing_columns], width="stretch", hide_index=True)
        st.bar_chart(score_df.set_index("prompt_id")["final_score"])

        if best_summary.get("best_prompt_text"):
            with st.expander("Best prompt text to reuse in overall project", expanded=False):
                st.code(best_summary["best_prompt_text"], language="text")

with tabs[3]:
    if expected_ready:
        expected_payload = read_json(paths["expected"])
        expected_outputs = expected_payload.get("expected_outputs", {})
        evidence_rows = [
            {
                "field": field,
                "value": payload.get("expected_value"),
                "page": payload.get("page_number"),
                "confidence": payload.get("confidence"),
            }
            for field, payload in expected_outputs.items()
            if payload.get("expected_value") is not None
        ]
        st.dataframe(pd.DataFrame(evidence_rows), width="stretch", hide_index=True)
    else:
        st.info("Evidence appears after expected output construction.")

    if extracted_ready:
        with st.expander("View extracted PDF text", expanded=False):
            extracted_payload = read_json(paths["extracted"])
            preview_page = st.number_input(
                "Page number",
                min_value=1,
                max_value=max(1, extracted_payload["page_count"]),
                value=1,
            )
            st.text_area("Page text", extracted_payload["pages"][preview_page - 1]["text"], height=220)

with tabs[4]:
    export_candidates = [
        paths["extracted"],
        paths["expected"],
        paths["scores_csv"],
        paths["scores_json"],
        paths["final_json"],
        paths["final_md"],
        EVALUATION_RESULTS_DIR / "best_prompt_summary.json",
        EVALUATION_RESULTS_DIR / "best_prompt_selection_report.md",
        EVALUATION_RESULTS_DIR / "best_prompt_to_use.txt",
        EVALUATION_RESULTS_DIR / "methodology_summary.md",
    ]
    available_exports = [path for path in export_candidates if path.exists()]
    if not available_exports:
        st.info("No export files are ready yet.")
    for export_path in available_exports:
        st.download_button(
            label=export_path.name,
            data=export_path.read_bytes(),
            file_name=export_path.name,
            width="stretch",
        )

with st.expander("Advanced manual controls", expanded=False):
    st.caption("Use these only if you want to run one pipeline stage manually.")
    manual_cols = st.columns(4)
    if manual_cols[0].button("Extract Text"):
        run_action("PDF text extraction", lambda: save_extracted_pdf(ANNUAL_REPORTS_DIR / selected_pdf))
    if manual_cols[1].button("Build Expected"):
        run_action("Expected output construction", lambda: build_selected_expected(selected_pdf))
    if manual_cols[2].button("Run 10 Prompts"):
        run_action("10 prompt benchmark", lambda: run_benchmark(report_name=selected_pdf))
    if manual_cols[3].button("Evaluate + Final"):
        run_action("Evaluation and final report", lambda: evaluate_and_generate_selected(selected_pdf))
