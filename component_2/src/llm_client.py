"""Azure OpenAI client wrapper.

This is the only file that talks to Azure OpenAI. It loads credentials from
environment variables, retries transient failures, parses JSON safely, and never
prints the API key.
"""

from __future__ import annotations

import os
import time
from typing import Any

from .config import get_azure_settings, load_environment
from .utils import json_loads_safe


SYSTEM_PROMPT = (
    "You extract source-grounded investor-related information from annual report text. "
    "Return only valid JSON. "
    "Never fabricate missing values. "
    "Never provide buy, sell, or hold advice. "
    "Every important fact must be grounded in the supplied report context."
)


class LLMClient:
    """Azure OpenAI wrapper with retry, timeout, and JSON-safe parsing."""

    def __init__(self, timeout_seconds: int = 120, max_retries: int = 3) -> None:
        try:
            from openai import AzureOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "Missing Azure OpenAI dependency. Run `python3 -m pip install openai` "
                "or install everything with `python3 -m pip install -r requirements.txt` from component_2."
            ) from exc

        load_environment()
        settings = get_azure_settings()
        required = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY"]
        missing = [key for key in required if not settings.get(key)]
        if missing:
            raise ValueError(f"Missing Azure OpenAI settings: {', '.join(missing)}")

        self.deployment = settings["AZURE_OPENAI_DEPLOYMENT"]
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.client = AzureOpenAI(
            azure_endpoint=settings["AZURE_OPENAI_ENDPOINT"],
            api_key=settings["AZURE_OPENAI_API_KEY"],
            api_version=settings["AZURE_OPENAI_API_VERSION"],
            timeout=timeout_seconds,
        )

    def run_json_prompt(self, prompt_input: str, instructions: str = SYSTEM_PROMPT) -> dict[str, Any]:
        """Execute one Azure OpenAI prompt and return a safe structured result."""
        last_error: Exception | None = None
        started_at = time.perf_counter()

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.responses.create(
                    model=self.deployment,
                    instructions=instructions,
                    input=prompt_input,
                )
                raw_output = (response.output_text or "").strip()
                parsed_output = json_loads_safe(raw_output)
                usage = getattr(response, "usage", None)
                return {
                    "raw_output": raw_output,
                    "parsed_output": parsed_output,
                    "usage": {
                        "input_tokens": getattr(usage, "input_tokens", None) if usage else None,
                        "output_tokens": getattr(usage, "output_tokens", None) if usage else None,
                        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
                    },
                    "runtime_seconds": round(time.perf_counter() - started_at, 3),
                    "error": None,
                }
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == self.max_retries:
                    break
                time.sleep(min(2**attempt, 8))

        return {
            "raw_output": "",
            "parsed_output": None,
            "usage": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
            "runtime_seconds": round(time.perf_counter() - started_at, 3),
            "error": str(last_error) if last_error else "Unknown LLM error.",
        }
