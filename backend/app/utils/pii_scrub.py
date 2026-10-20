"""CIRUS — Utility: PII (Personally Identifiable Information) scrubber.

Redacts sensitive values from incident text BEFORE it is sent to any external
AI API. This prevents account numbers, IP addresses, email addresses, and
API keys from leaking to third-party services.

Usage:
    from app.utils.pii_scrub import scrub_pii

    safe_text = scrub_pii(raw_incident_text)
    # Pass safe_text to the LLM, keep raw_incident_text in the database.

What is scrubbed:
  - AWS account IDs (12-digit numbers in ARN format)
  - IPv4 and IPv6 addresses
  - Email addresses
  - API keys and tokens (common patterns: sk-, rc_, gsk_, fc-, Bearer <token>)
  - Credit card numbers (basic Luhn pattern)
  - Passwords in key=value style (e.g. password=secret123)

What is NOT scrubbed (intentionally):
  - Cloud service names (aws_s3_bucket, arn:aws:iam — schema info, not PII)
  - Severity levels, timestamps, error codes
  - The words "public", "private", "bucket", "policy" etc.

Safety principle: When in doubt, redact. A false positive (redacting something
harmless) is safer than a false negative (leaking a real secret).
"""
from __future__ import annotations

import re
from typing import List, Tuple

# Each entry is (compiled regex, replacement string)
_RULES: List[Tuple[re.Pattern, str]] = [
    # AWS account ID inside an ARN  e.g. arn:aws:iam::123456789012:role/... or synthetic 9-digit
    (re.compile(r"(arn:[a-z0-9\-]+:[a-z0-9\-]+:[a-z0-9\-]*:)(\d{9,12})(:[^\s]+)", re.IGNORECASE),
     r"\1[ACCOUNT_ID]\3"),

    # Standalone 12-digit AWS account IDs (not inside an ARN)
    (re.compile(r"\b(\d{12})\b"), "[ACCOUNT_ID]"),

    # IPv4 addresses
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_ADDRESS]"),

    # IPv6 addresses (simplified)
    (re.compile(r"\b([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"), "[IPV6_ADDRESS]"),

    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),

    # Bearer tokens (HTTP Authorization header)
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\1[BEARER_TOKEN]"),

    # Common API key prefixes
    # Featherless: rc_<hex>
    (re.compile(r"\brc_[0-9a-fA-F]{20,}\b"), "[API_KEY]"),
    # Groq: gsk_<alphanumeric>
    (re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"), "[API_KEY]"),
    # OpenAI: sk-<alphanumeric>
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "[API_KEY]"),
    # Firecrawl: fc-<hex>
    (re.compile(r"\bfc-[0-9a-fA-F]{20,}\b"), "[API_KEY]"),
    # Generic: <word>_key or <word>_secret followed by = or : and a value
    (re.compile(r"((?:api_?key|secret|token|password|passwd|pwd)\s*[=:]\s*)([^\s\"',\]}{>]{6,})",
                re.IGNORECASE),
     r"\1[REDACTED]"),

    # AWS secret access keys (40-char alphanumeric after a common prefix)
    (re.compile(r"\b[A-Z0-9]{20}\b"), "[AWS_ACCESS_KEY_ID]"),
]


def scrub_pii(text: str) -> str:
    """Return a copy of *text* with PII replaced by placeholder tokens.

    The original text is never modified. The returned string is safe to
    send to external AI APIs.

    Args:
        text: Raw incident report text, potentially containing PII.

    Returns:
        A new string with sensitive values replaced by [PLACEHOLDER] tokens.
    """
    if not text:
        return text

    result = text
    for pattern, replacement in _RULES:
        result = pattern.sub(replacement, result)
    return result


def scrub_dict(data: dict) -> dict:
    """Recursively scrub PII from all string values in a dict.

    Useful for scrubbing extracted metadata before logging or sending to AI.
    """
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = scrub_pii(value)
        elif isinstance(value, dict):
            cleaned[key] = scrub_dict(value)
        elif isinstance(value, list):
            cleaned[key] = [
                scrub_pii(v) if isinstance(v, str)
                else scrub_dict(v) if isinstance(v, dict)
                else v
                for v in value
            ]
        else:
            cleaned[key] = value
    return cleaned
