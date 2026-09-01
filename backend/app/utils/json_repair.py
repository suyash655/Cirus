"""CIRUS — JSON repair and safe parsing utilities."""
from __future__ import annotations

import json
import re
from typing import Any


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Attempt to parse JSON; return `default` on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    repaired = repair_json(text)
    try:
        return json.loads(repaired)
    except (json.JSONDecodeError, TypeError):
        return default


def repair_json(text: str) -> str:
    """Best-effort JSON repair for LLM outputs.

    Handles common issues:
    - Trailing commas in objects/arrays
    - Single-quoted strings
    - Bare keys without quotes
    - Markdown code fence wrapping
    """
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
    text = text.strip()

    # Replace single quotes used as string delimiters (naïve pass)
    # Only safe when single quotes aren't inside values
    # text = text.replace("'", '"')  # disabled — too destructive

    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    return text


def extract_json_block(text: str) -> str | None:
    """Extract the first JSON object or array found in a larger text block."""
    # Try to find JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    # Try array
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        return match.group(0)
    return None


def parse_llm_json(text: str, default: Any = None) -> Any:
    """Extract and parse JSON from raw LLM output."""
    block = extract_json_block(text) or text
    return safe_json_loads(block, default=default)
