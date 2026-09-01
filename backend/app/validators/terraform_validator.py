"""CIRUS — Validators: Terraform HCL AST-level syntax validator.

Validates Terraform HCL using `python-hcl2` for parsing and optionally
`terraform validate` for full schema validation.

WHY NOT AN LLM SELF-CHECK:
LLMs produce Terraform that looks correct but fails validation due to:
  - Unclosed brackets / mismatched braces (especially in heredoc strings)
  - Invalid attribute names that match no resource schema
  - `count` used alongside `for_each` on the same resource
  - Circular references between modules
  - Invalid provider requirement syntax

`terraform validate` catches these; an LLM asked to review its own output
will confidently declare them valid because they "look reasonable."
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
    validator_used: str = "regex"  # "terraform" | "hcl2" | "regex" | "skipped"


# ── HCL2 parser (structural) ──────────────────────────────────────────────────

def _hcl2_validate(content: str) -> ValidationResult:
    """Parse HCL using python-hcl2. Catches structural/syntax errors."""
    try:
        import hcl2
        import io
        hcl2.load(io.StringIO(content))
        return ValidationResult(valid=True, validator_used="hcl2")
    except ImportError:
        return ValidationResult(valid=True, validator_used="skipped")  # Fall to regex
    except Exception as e:
        return ValidationResult(valid=False, error=str(e), validator_used="hcl2")


# ── Regex canary (last resort) ────────────────────────────────────────────────

def _regex_validate_terraform(content: str) -> ValidationResult:
    """Structural sanity checks for HCL content."""
    # Count braces
    open_braces = content.count("{")
    close_braces = content.count("}")
    if open_braces != close_braces:
        return ValidationResult(
            valid=False,
            error=f"mismatched braces: {open_braces} open vs {close_braces} close",
            validator_used="regex",
        )

    # Must have at least one block
    if not re.search(r'(resource|data|variable|output|module|locals|provider|terraform)\s+"', content):
        if not re.search(r"(resource|data|variable|output|module|locals|provider|terraform)\s*\{", content):
            return ValidationResult(
                valid=False,
                error="no valid Terraform blocks found",
                validator_used="regex",
            )

    return ValidationResult(valid=True, validator_used="regex")


# ── Terraform CLI validator (authoritative) ───────────────────────────────────

def _terraform_validate(content: str) -> ValidationResult:
    """
    Run `terraform validate` against the HCL content.
    Requires `terraform init` to have been run in a temp dir with the content.
    This is authoritative but slow (2-5s per call due to init).
    """
    tf_bin = shutil.which("terraform")
    if not tf_bin:
        return ValidationResult(valid=True, validator_used="skipped")

    with tempfile.TemporaryDirectory() as tmpdir:
        tf_file = os.path.join(tmpdir, "main.tf")
        with open(tf_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Write a minimal providers.tf to avoid provider lookup errors
        providers_tf = os.path.join(tmpdir, "providers.tf")
        with open(providers_tf, "w", encoding="utf-8") as f:
            f.write('terraform {\n  required_providers {\n    aws = {\n      source = "hashicorp/aws"\n    }\n  }\n}\n')

        # init (skip provider download)
        init_result = subprocess.run(
            [tf_bin, "init", "-backend=false", "-input=false"],
            capture_output=True, text=True, cwd=tmpdir, timeout=30,
        )
        if init_result.returncode != 0:
            # Init failed — fall back to hcl2 parsing instead of failing
            return _hcl2_validate(content)

        # validate
        val_result = subprocess.run(
            [tf_bin, "validate", "-json"],
            capture_output=True, text=True, cwd=tmpdir, timeout=30,
        )
        if val_result.returncode != 0:
            try:
                import json
                data = json.loads(val_result.stdout)
                diagnostics = data.get("diagnostics", [])
                msgs = "; ".join(d.get("summary", "") for d in diagnostics[:3])
                return ValidationResult(valid=False, error=msgs or "terraform validate failed", validator_used="terraform")
            except Exception:
                return ValidationResult(valid=False, error=val_result.stdout[:500], validator_used="terraform")
        return ValidationResult(valid=True, validator_used="terraform")


# ── Public API ────────────────────────────────────────────────────────────────

def validate_terraform(content: str) -> ValidationResult:
    """
    Validate Terraform HCL. Priority order:
    1. python-hcl2 parsing (fast, structural)
    2. `terraform validate` (full schema validation, slower)
    3. regex canary (brace counting + block detection)
    """
    if not content or not content.strip():
        return ValidationResult(valid=False, error="empty content", validator_used="regex")

    # Try hcl2 first (fast)
    hcl2_result = _hcl2_validate(content)
    if hcl2_result.validator_used == "skipped":
        # hcl2 not installed — fall to regex
        return _regex_validate_terraform(content)
    if not hcl2_result.valid:
        return hcl2_result

    # hcl2 passed — try terraform validate for full schema check
    tf_result = _terraform_validate(content)
    if tf_result.validator_used == "skipped":
        return hcl2_result  # Return the hcl2 result as best effort

    return tf_result
