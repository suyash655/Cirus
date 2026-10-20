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

    for pattern, msg in _SUSPICIOUS_PATTERNS:
        if pattern.search(code):
            return ValidationResult(valid=False, error=msg, validator_used="regex")

    # Must have at least one rule definition or assignment
    # Supports classic Rego (`deny[msg] {`), Rego v1 (`deny if {`, `deny contains msg if {`),
    # assignments (`is_admin := true`), and defaults (`default allow := false`).
    rule_pattern = re.compile(
        r"^\s*(?:default\s+)?\w+(?:\[[^\]]*\])?(?:\s+contains\s+\w+)?(?:\s*:=\s*|\s+if\b|\s*\{)",
        re.MULTILINE,
    )
    if not rule_pattern.search(code):
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


def test_rego(policy_code: str, test_code: str) -> ValidationResult:
    """
    Run `opa test` against policy and test snippets.
    Authoritative when opa binary is installed; falls back to validating
    the syntax of both files when opa is absent.
    """
    if not policy_code or not policy_code.strip():
        return ValidationResult(valid=False, error="empty policy code", validator_used="regex")
    if not test_code or not test_code.strip():
        return ValidationResult(valid=False, error="empty test code", validator_used="regex")

    opa_bin = shutil.which("opa")
    if not opa_bin:
        p_res = validate_rego(policy_code)
        if not p_res.valid:
            return p_res
        t_res = validate_rego(test_code)
        if not t_res.valid:
            return ValidationResult(valid=False, error=f"Test syntax error: {t_res.error}", validator_used="regex")
        return ValidationResult(valid=True, validator_used="regex")

    with tempfile.TemporaryDirectory() as tmpdir:
        p_path = os.path.join(tmpdir, "policy.rego")
        t_path = os.path.join(tmpdir, "policy_test.rego")
        with open(p_path, "w", encoding="utf-8") as f:
            f.write(policy_code)
        with open(t_path, "w", encoding="utf-8") as f:
            f.write(test_code)

        try:
            result = subprocess.run(
                [opa_bin, "test", p_path, t_path, "-v"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout or "opa test failed").strip()
                return ValidationResult(valid=False, error=err, validator_used="opa")
            return ValidationResult(valid=True, validator_used="opa")
        except subprocess.TimeoutExpired:
            return ValidationResult(valid=False, error="opa test timed out (>15s)", validator_used="opa")
