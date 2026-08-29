"""Reusable helpers for files, text cleanup, JSON parsing, and scoring."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    """Convert a file/company name into a safe lowercase artifact name."""
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()


def read_json(path: Path) -> Any:
    """Read a UTF-8 JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with stable indentation and Unicode support."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    """Write a Markdown text file, creating folders if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def normalize_whitespace(value: str) -> str:
    """Collapse repeated whitespace into single spaces."""
    return " ".join(value.split())


def safe_excerpt(text: str, start: int, end: int, window: int = 140) -> str:
    """Return a short snippet around a matched text span."""
    left = max(0, start - window)
    right = min(len(text), end + window)
    return normalize_whitespace(text[left:right])


def flatten_text(value: Any) -> str:
    """Convert nested prompt values into comparable plain text."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return "; ".join(flatten_text(item) for item in value)
    return str(value)


def extract_json_candidate(text: str) -> str:
    """Extract the JSON object from a raw model response."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first != -1 and last != -1 and last > first:
        return stripped[first : last + 1]
    return stripped


def json_loads_safe(text: str) -> Any:
    """Parse JSON after removing optional markdown fences or surrounding text."""
    return json.loads(extract_json_candidate(text))


def scan_pdf_files(directory: Path) -> list[Path]:
    """Return sorted PDF files in a directory."""
    return sorted(directory.glob("*.pdf"))


MULTIPLIER_BY_UNIT = {
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "trillion": 1_000_000_000_000,
}


def numeric_from_text(value: Any) -> float | None:
    """Normalize a textual number with units into a float."""
    text = flatten_text(value).lower().replace(",", " ")
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not numbers:
        return None
    number = float(numbers[0])
    multiplier = 1.0
    for unit, unit_multiplier in MULTIPLIER_BY_UNIT.items():
        if unit in text:
            multiplier = float(unit_multiplier)
            break
    if "%" in text:
        return number / 100.0
    return number * multiplier


def similar_numeric(expected: Any, predicted: Any, tolerance: float = 0.05) -> float:
    """Score numeric similarity from 0 to 1 using relative error tolerance."""
    expected_number = numeric_from_text(expected)
    predicted_number = numeric_from_text(predicted)
    if expected_number is None or predicted_number is None:
        return 0.0
    if expected_number == 0:
        return 1.0 if abs(predicted_number) < 1e-9 else 0.0
    relative_error = abs(predicted_number - expected_number) / abs(expected_number)
    return max(0.0, 1.0 - min(1.0, relative_error / tolerance))


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Clamp a score into the configured range."""
    return max(lower, min(upper, value))


def ordered_merge(primary: dict[str, Any], secondary: dict[str, Any]) -> OrderedDict[str, Any]:
    """Merge dictionaries while preserving primary key order."""
    merged: OrderedDict[str, Any] = OrderedDict()
    for key, value in primary.items():
        merged[key] = value
    for key, value in secondary.items():
        if key not in merged:
            merged[key] = value
    return merged


def has_meaningful_value(value: Any) -> bool:
    """Return False for missing/null/not-found style values."""
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip().lower()
        return bool(stripped) and stripped not in {"not found", "null", "none", "n/a"}
    if isinstance(value, list):
        return any(has_meaningful_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_meaningful_value(item) for item in value.values())
    return True


def cosine_similarity_fallback(a: str, b: str) -> float:
    """Compute cosine similarity using simple token counts."""
    tokens_a = Counter(tokenize_text(a))
    tokens_b = Counter(tokenize_text(b))
    if not tokens_a or not tokens_b:
        return 0.0
    dot = sum(tokens_a[token] * tokens_b.get(token, 0) for token in tokens_a)
    mag_a = math.sqrt(sum(value * value for value in tokens_a.values()))
    mag_b = math.sqrt(sum(value * value for value in tokens_b.values()))
    if not mag_a or not mag_b:
        return 0.0
    return dot / (mag_a * mag_b)


def tokenize_text(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r"[a-z0-9]+", text.lower())
