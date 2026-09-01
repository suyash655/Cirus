"""CIRUS — Validators: Rego (OPA) AST-level syntax validator.

Calls the OPA binary (`opa check`) if available, falls back to regex-based
structural parsing. The OPA binary check is authoritative; regex is a
canary that flags obvious structural problems when OPA is not installed.

WHY NOT AN LLM SELF-CHECK:
LLMs routinely produce Rego that "looks right" — correct package declaration,
plausible rule names, no obvious typos — but fails `opa check` due to:
  - Missing `import rego.v1` when using `every` / `in` keywords
  - References to undefined variables or rules
  - Incorrect rule bodies that OPA's unifier rejects
  - Invalid `with` clause targeting
An LLM asked to verify its own output will often approve these errors.
Only a real parser call catches them.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    valid: bool
    error: Optional[str] = None
    validator_used: str = "regex"  # "opa" | "regex" | "skipped"


# ── Regex-based structural validator (canary) ─────────────────────────────────

_REQUIRED_PATTERNS = [
    (re.compile(r"^\s*package\s+\w[\w.]*", re.MULTILINE), "missing `package` declaration"),
]

_SUSPICIOUS_PATTERNS = [
    (re.compile(r"\bdefault\s+\w+\s*:=\s*$", re.MULTILINE), "bare `default` assignment with no value"),
    (re.compile(r"\{\s*\}", re.MULTILINE), "empty rule body `{}`"),
]


def _regex_validate_rego(code: str) -> ValidationResult:
    """Structural sanity check for Rego code."""
    for pattern, msg in _REQUIRED_PATTERNS:
        if not pattern.search(code):
            return ValidationResult(valid=False, error=msg, validator_used="regex")

    # Must have at least one rule definition
    if not re.search(r"^\s*(allow|deny|violation|warn|\w+)\s*\{", code, re.MULTILINE):
        if not re.search(r"^\s*\w+\s*:=", code, re.MULTILINE):
            return ValidationResult(
                valid=False,
                error="no rule or assignment found — policy body appears empty",
                validator_used="regex",
            )

    return ValidationResult(valid=True, validator_used="regex")


# ── OPA binary validator (authoritative) ─────────────────────────────────────

def _opa_validate_rego(code: str) -> ValidationResult:
    """Run `opa check` against the Rego snippet. Authoritative AST parse."""
    opa_bin = shutil.which("opa")
    if not opa_bin:
        return ValidationResult(
            valid=True,
            error=None,
            validator_used="skipped",  # OPA not installed; fall through to regex
        )

    with tempfile.NamedTemporaryFile(
        suffix=".rego", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [opa_bin, "check", tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            error_msg = (result.stderr or result.stdout or "unknown OPA error").strip()
            return ValidationResult(valid=False, error=error_msg, validator_used="opa")
        return ValidationResult(valid=True, validator_used="opa")
    except subprocess.TimeoutExpired:
        return ValidationResult(
            valid=False,
            error="OPA check timed out (>15s)",
            validator_used="opa",
        )
    finally:
        os.unlink(tmp_path)


# ── Public API ────────────────────────────────────────────────────────────────

def validate_rego(code: str) -> ValidationResult:
    """
    Validate Rego code. Tries OPA binary first (authoritative), falls back
    to regex structural check. Returns ValidationResult with .valid and .error.
    """
    if not code or not code.strip():
        return ValidationResult(valid=False, error="empty code", validator_used="regex")

    # Try OPA first
    opa_result = _opa_validate_rego(code)
    if opa_result.validator_used == "skipped":
        # OPA not available — use regex canary
        return _regex_validate_rego(code)

    return opa_result
