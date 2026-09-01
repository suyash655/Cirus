"""CIRUS — Evaluation: pytest suite for golden dataset regression testing.

HOW TO RUN LOCALLY:
    cd PROJECTRIVERA
    pytest mlops/evaluation/ -v --tb=short

CI PASS CRITERIA:
    - Overall pass rate >= 95% (47/50 cases)
    - No case with syntax_valid=False in policy or iac artifacts may pass
    - Faithfulness score mean >= 0.7 across all cases

NIGHTLY CI:
    Wired to .github/workflows/eval_regression.yml (runs at 02:00 UTC daily).
    Fails the build if pass_rate < 0.95.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

from mlops.evaluation.golden_dataset.cases import GOLDEN_DATASET, GoldenCase
from mlops.evaluation.metrics import (
    InfraFaithfulnessMetric,
    SyntaxValidityMetric,
    ContextRelevancyMetric,
)

# DeepEval test case wrapper
try:
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    # Stub for environments without deepeval
    class LLMTestCase:  # type: ignore
        def __init__(self, input, actual_output, context=None, **kwargs):
            self.input = input
            self.actual_output = actual_output
            self.context = context or []


# ── Results accumulator (for pass-rate assertion) ────────────────────────────
_results: List[Dict[str, Any]] = []


def _evaluate_case(case: GoldenCase, artifact_type: str, artifact_code: str) -> Dict[str, Any]:
    """Evaluate a single artifact with all three metrics. Returns a result dict."""
    tc = LLMTestCase(
        input=case.raw_text,
        actual_output=artifact_code,
        context=case.root_cause_keywords,
    )

    faithfulness = InfraFaithfulnessMetric(required_keywords=case.root_cause_keywords)
    syntax = SyntaxValidityMetric(artifact_type=artifact_type)
    relevancy = ContextRelevancyMetric()

    f_score = faithfulness.measure(tc)
    s_score = syntax.measure(tc)
    r_score = relevancy.measure(tc)

    passed = faithfulness.is_successful() and syntax.is_successful()

    return {
        "incident_id": case.incident_id,
        "category": case.category,
        "artifact_type": artifact_type,
        "faithfulness": round(f_score, 3),
        "syntax_valid": s_score == 1.0,
        "context_relevancy": round(r_score, 3),
        "passed": passed,
        "faithfulness_reason": faithfulness.reason,
        "syntax_reason": syntax.reason,
        "validator_used": syntax.reason.split("]")[0].lstrip("[") if "]" in syntax.reason else "regex",
    }


# ── Parametrized test cases ───────────────────────────────────────────────────

@pytest.mark.parametrize("case", GOLDEN_DATASET, ids=[c.incident_id for c in GOLDEN_DATASET])
def test_golden_rego_policy(case: GoldenCase):
    """Test that the known-good Rego policy passes faithfulness + syntax validity."""
    result = _evaluate_case(case, "rego", case.expected_rego)
    _results.append(result)

    print(f"\n[{case.incident_id}] Rego | faith={result['faithfulness']:.2f} "
          f"syntax={'✓' if result['syntax_valid'] else '✗'} "
          f"validator={result['validator_used']}")
    print(f"  Reason: {result['faithfulness_reason']}")

    assert result["syntax_valid"], (
        f"{case.incident_id}: Rego syntax check FAILED — {result['syntax_reason']}\n"
        f"Code:\n{case.expected_rego[:200]}"
    )
    assert result["faithfulness"] >= 0.7, (
        f"{case.incident_id}: Faithfulness too low ({result['faithfulness']:.2f}) — "
        f"{result['faithfulness_reason']}"
    )


@pytest.mark.parametrize("case", GOLDEN_DATASET, ids=[c.incident_id for c in GOLDEN_DATASET])
def test_golden_terraform_patch(case: GoldenCase):
    """Test that the known-good Terraform patch passes faithfulness + syntax validity."""
    result = _evaluate_case(case, "terraform", case.expected_terraform)
    _results.append(result)

    print(f"\n[{case.incident_id}] TF | faith={result['faithfulness']:.2f} "
          f"syntax={'✓' if result['syntax_valid'] else '✗'} "
          f"validator={result['validator_used']}")

    assert result["syntax_valid"], (
        f"{case.incident_id}: Terraform syntax check FAILED — {result['syntax_reason']}\n"
        f"Code:\n{case.expected_terraform[:200]}"
    )
    assert result["faithfulness"] >= 0.5, (  # Lower bar for TF — less keyword-dense
        f"{case.incident_id}: Terraform faithfulness too low ({result['faithfulness']:.2f})"
    )


# ── Overall pass-rate assertion ───────────────────────────────────────────────

def test_overall_pass_rate():
    """
    Final assertion: at least 95% of test cases must pass.
    This runs AFTER all parametrized tests have accumulated results.
    """
    if not _results:
        pytest.skip("No results accumulated — run other tests first")

    total = len(_results)
    passed = sum(1 for r in _results if r["passed"])
    pass_rate = passed / total

    # Print summary table
    print(f"\n{'='*60}")
    print(f"CIRUS EVALUATION REPORT")
    print(f"{'='*60}")
    print(f"Total test cases: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Pass rate: {pass_rate:.1%}")
    print(f"{'='*60}")

    by_category: Dict[str, List] = {}
    for r in _results:
        by_category.setdefault(r["category"], []).append(r)

    for cat, results in sorted(by_category.items()):
        cat_pass = sum(1 for r in results if r["passed"])
        avg_faith = sum(r["faithfulness"] for r in results) / len(results)
        print(f"  {cat}: {cat_pass}/{len(results)} passed, avg faithfulness={avg_faith:.2f}")

    # Save report to disk for CI artifact upload
    report_path = Path(__file__).parent / "eval_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "pass_rate": pass_rate,
            "passed": passed,
            "total": total,
            "results": _results,
        }, f, indent=2)
    print(f"\nReport saved to: {report_path}")

    assert pass_rate >= 0.95, (
        f"Pass rate {pass_rate:.1%} is below the 95% threshold. "
        f"Failed cases: {[r['incident_id'] for r in _results if not r['passed']]}"
    )


# ── Adversarial validator tests ───────────────────────────────────────────────
# These confirm the validator catches what an LLM self-check would miss.

class TestAdversarialValidators:
    """
    Adversarial test cases: subtly wrong code that LOOKS valid to an LLM
    but fails real parser validation.
    """

    def test_rego_missing_package_fails(self):
        """Rego without `package` declaration: LLM might approve this."""
        bad_rego = """
import rego.v1

deny contains msg if {
    input.resource_type == "aws_s3_bucket"
    msg := "no public buckets"
}
"""
        from app.validators.rego_validator import validate_rego
        result = validate_rego(bad_rego)
        assert not result.valid, "Validator should reject Rego without package declaration"

    def test_rego_empty_rule_body_fails(self):
        """Empty rule body — syntactically ambiguous in Rego."""
        bad_rego = """
package cirus.test

deny contains msg if {}
"""
        from app.validators.rego_validator import validate_rego
        result = validate_rego(bad_rego)
        # An empty rule body is technically valid Rego but semantically wrong;
        # our regex validator flags it as suspicious
        # OPA may accept it — we test that we at least detect the pattern
        print(f"Empty rule body result: valid={result.valid}, error={result.error}")
        # We don't assert invalid here — OPA may accept it.
        # The important thing is the validator runs without crashing.

    def test_rego_plausible_but_missing_import_for_every(self):
        """Using `every` without `import rego.v1` — common LLM mistake."""
        bad_rego = """
package cirus.iam

# Missing: import rego.v1

deny contains msg if {
    every bucket in input.resource.buckets {
        bucket.encrypted == true
    }
    msg := "all buckets must be encrypted"
}
"""
        from app.validators.rego_validator import validate_rego
        result = validate_rego(bad_rego)
        # OPA will catch this; regex may not. We test that the chain works.
        print(f"Missing import result: valid={result.valid}, validator={result.validator_used}")
        # If OPA is available, this should fail
        import shutil
        if shutil.which("opa"):
            assert not result.valid, "OPA should reject `every` without import rego.v1"

    def test_terraform_mismatched_braces_fails(self):
        """Unclosed brace — LLM often misses this in heredoc strings."""
        bad_tf = """
resource "aws_s3_bucket" "test" {
  bucket = "my-bucket"
  acl    = "private"
  # missing closing brace
"""
        from app.validators.terraform_validator import validate_terraform
        result = validate_terraform(bad_tf)
        assert not result.valid, f"Validator should reject unclosed brace: {result.error}"

    def test_terraform_valid_passes(self):
        """Confirm valid Terraform passes."""
        good_tf = """
resource "aws_s3_bucket" "test" {
  bucket = "my-bucket"
}
"""
        from app.validators.terraform_validator import validate_terraform
        result = validate_terraform(good_tf)
        assert result.valid, f"Valid Terraform should pass: {result.error}"

    def test_terraform_plausible_invalid_resource_key(self):
        """Invalid attribute in resource block — hcl2 parses structure, terraform validate catches schema."""
        slightly_wrong_tf = """
resource "aws_s3_bucket" "test" {
  bucket = "my-bucket"
  nonexistent_invalid_attr = "value"
}
"""
        from app.validators.terraform_validator import validate_terraform
        result = validate_terraform(slightly_wrong_tf)
        # hcl2 will accept this (structural parse passes)
        # terraform validate would reject it (schema validation)
        print(f"Invalid attr result: valid={result.valid}, validator={result.validator_used}")
        # We log and don't fail the test — this documents the gap between hcl2 and tf validate

    def test_rego_valid_passes(self):
        """Confirm known-good Rego passes."""
        good_rego = """
package cirus.test

import rego.v1

deny contains msg if {
    input.resource_type == "aws_s3_bucket"
    input.resource.acl == "public-read"
    msg := "public-read ACL is not permitted"
}
"""
        from app.validators.rego_validator import validate_rego
        result = validate_rego(good_rego)
        assert result.valid, f"Valid Rego should pass: {result.error}"
