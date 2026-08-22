"""Central paths and environment loading for Component 2.

All scripts import paths from here instead of hardcoding folders. Azure OpenAI
settings are read from `.env` only and are never printed.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ANNUAL_REPORTS_DIR = DATA_DIR / "annual_reports"
EXTRACTED_TEXT_DIR = DATA_DIR / "extracted_text"
EXPECTED_OUTPUTS_DIR = DATA_DIR / "expected_outputs"
PROMPT_OUTPUTS_DIR = DATA_DIR / "prompt_outputs"
EVALUATION_RESULTS_DIR = DATA_DIR / "evaluation_results"
FINAL_INSIGHTS_DIR = DATA_DIR / "final_insights"
APP_DIR = BASE_DIR / "app"
TESTS_DIR = BASE_DIR / "tests"


def load_environment() -> None:
    """Load environment variables from the local .env file if present."""
    load_dotenv(BASE_DIR / ".env")


def ensure_directories() -> None:
    """Create component data directories on demand."""
    for path in [
        DATA_DIR,
        ANNUAL_REPORTS_DIR,
        EXTRACTED_TEXT_DIR,
        EXPECTED_OUTPUTS_DIR,
        PROMPT_OUTPUTS_DIR,
        EVALUATION_RESULTS_DIR,
        FINAL_INSIGHTS_DIR,
        APP_DIR,
        TESTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def get_azure_settings() -> dict[str, str]:
    """Return Azure OpenAI settings without printing sensitive values."""
    load_environment()
    keys = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_RESOURCE_NAME",
        "AZURE_OPENAI_API_KEY",
    ]
    return {key: os.getenv(key, "") for key in keys}
