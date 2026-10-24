"""Private explanation providers with a shared JSON result contract."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse

import requests

from .config import get_azure_settings, load_environment
from .utils import json_loads_safe


SYSTEM_PROMPT = (
    "You extract source-grounded investor-related information from annual report text. "
    "Return only valid JSON. "
    "Never fabricate missing values. "
    "Never provide buy, sell, or hold advice. "
    "Every important fact must be grounded in the supplied report context."
)


def explanation_provider() -> str:
    load_environment()
    return os.getenv("LLM_PROVIDER", "azure").strip().lower()


def explanation_enabled() -> bool:
    provider = explanation_provider()
    if provider == "ollama":
        return True
    if provider == "disabled":
        return False
    return os.getenv("USE_AZURE_OPENAI", "false").strip().lower() in {"1", "true", "yes"}


class LLMClient:
    """Use the explicitly selected provider; never silently switch to cloud."""

    def __init__(self, timeout_seconds: int = 120, max_retries: int = 3) -> None:
        load_environment()
        self.provider = explanation_provider()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        if self.provider == "ollama":
            self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
            url = urlparse(self.base_url)
            if (url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "::1"}
                    or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}):
                raise ValueError("Local explanations require a loopback Ollama address.")
            self.deployment = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
            self.session = requests.Session()
            self.session.trust_env = False
            return
        if self.provider != "azure":
            raise ValueError("Select azure or ollama as the explanation provider.")
        try:
            from openai import AzureOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "Missing Azure OpenAI dependency. Run `python3 -m pip install openai` "
                "or install everything with `python3 -m pip install -r requirements.txt` from component_2."
            ) from exc

        settings = get_azure_settings()
        required = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY"]
        missing = [key for key in required if not settings.get(key)]
        if missing:
            raise ValueError(f"Missing Azure OpenAI settings: {', '.join(missing)}")

        self.deployment = settings["AZURE_OPENAI_DEPLOYMENT"]
        self.client = AzureOpenAI(
            azure_endpoint=settings["AZURE_OPENAI_ENDPOINT"],
            api_key=settings["AZURE_OPENAI_API_KEY"],
            api_version=settings["AZURE_OPENAI_API_VERSION"],
            timeout=timeout_seconds,
            max_retries=0,
        )

    def _local_response(self, prompt_input, instructions):
        # Reject oversized inputs rather than silently losing report context.
        maximum = int(os.getenv("OLLAMA_MAX_INPUT_CHARACTERS", "16000"))
        if len(prompt_input) + len(instructions) > maximum:
            raise ValueError("Local explanation input exceeds its configured limit.")
        response = self.session.post(f"{self.base_url}/api/chat", json={
            "model": self.deployment, "stream": False, "think": False,
            "format": "json", "keep_alive": "10m",
            "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": prompt_input}],
            "options": {"temperature": 0, "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
                        "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))},
        }, timeout=(5, self.timeout_seconds), allow_redirects=False)
        if response.status_code != 200:
            raise RuntimeError(f"Local explanation service returned HTTP {response.status_code}.")
        payload = response.json()
        if payload.get("done") is not True or payload.get("done_reason") == "length":
            raise ValueError("The local explanation was incomplete.")
        raw = payload.get("message", {}).get("content", "").strip()
        return raw, {"input_tokens": payload.get("prompt_eval_count"), "output_tokens": payload.get("eval_count"),
                     "total_tokens": (payload.get("prompt_eval_count") or 0) + (payload.get("eval_count") or 0)}

    def run_json_prompt(self, prompt_input: str, instructions: str = SYSTEM_PROMPT) -> dict[str, Any]:
        """Execute on the configured provider and validate complete JSON."""
        last_error: Exception | None = None
        started_at = time.perf_counter()

        attempts = 1 if self.provider == "ollama" else self.max_retries
        for attempt in range(1, attempts + 1):
            try:
                if self.provider == "ollama":
                    raw_output, usage_values = self._local_response(prompt_input, instructions)
                else:
                    response = self.client.responses.create(model=self.deployment, instructions=instructions, input=prompt_input)
                    raw_output = (response.output_text or "").strip()
                    usage = getattr(response, "usage", None)
                    usage_values = {key: getattr(usage, key, None) if usage else None
                                    for key in ("input_tokens", "output_tokens", "total_tokens")}
                parsed_output = json_loads_safe(raw_output)
                if not isinstance(parsed_output, dict):
                    raise ValueError("The explanation did not return a JSON object.")
                return {
                    "raw_output": raw_output,
                    "parsed_output": parsed_output,
                    "usage": usage_values,
                    "provider": self.provider, "model": self.deployment,
                    "runtime_seconds": round(time.perf_counter() - started_at, 3),
                    "error": None,
                }
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == attempts:
                    break
                time.sleep(min(2**attempt, 8))

        return {
            "raw_output": "",
            "parsed_output": None,
            "usage": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
            "runtime_seconds": round(time.perf_counter() - started_at, 3),
            "error": str(last_error) if last_error else "Unknown LLM error.",
            "provider": self.provider,
        }
