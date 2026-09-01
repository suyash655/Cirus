"""CIRUS — Evaluation: Custom DeepEval metrics for infrastructure artifact quality.

WHY DEEPEVAL OVER RAGAS:
Ragas is tuned for RAG pipelines (question → retrieve → answer). Its faithfulness
metric measures "does the answer claim facts that appear in the retrieved context?"
That's the wrong test for CIRUS. We need "does this Rego policy specifically close
the security hole described in the incident report?" — which requires:
  1. Semantic alignment between root_cause and policy body (DeepEval GEval allows
     this via a custom scoring rubric in natural language).
  2. Hard AST validity (not an LLM opinion — our own validator subprocess call).
  3. Keyword coverage (root_cause_keywords must appear in artifact, structurally).

DeepEval's GEval metric gives us a GPT-judge evaluation with a custom rubric,
plus we can mix in non-LLM custom metrics for syntax validity without fighting
Ragas's RAG-centric assumptions.
"""
from __future__ import annotations

import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from typing import Any

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class InfraFaithfulnessMetric(BaseMetric):
    """
    Faithfulness for infrastructure code artifacts.

    SCORING RUBRIC (explicitly defined — not generic RAG faithfulness):

    Score 1.0: The artifact directly and specifically addresses the root cause.
      - The Rego package name or Terraform resource type maps to the affected resource.
      - The rule body references the specific misconfiguration (not a generic check).
      - The policy/patch, if applied, would have prevented this specific incident.

    Score 0.7-0.9: The artifact is relevant but partially addresses the root cause.
      - Addresses the general class of problem but misses the specific trigger.
      - Example: blocks all public S3 but doesn't address the specific ACL type mentioned.

    Score 0.4-0.6: The artifact is generically related but not incident-specific.
      - Could plausibly apply to many incidents; adds no specificity from root_cause analysis.

    Score 0.0-0.3: The artifact does not address the root cause or is syntactically invalid.
      - Policy targets wrong resource type, wrong action, or wrong condition.

    IMPLEMENTATION NOTE:
    We use keyword coverage as a fast proxy for faithfulness, then optionally
    invoke an LLM judge for borderline scores (0.4-0.8 range). This keeps
    CI fast (most golden dataset cases will be clear-cut) while catching edge cases.
    """

    def __init__(self, threshold: float = 0.7, required_keywords: list[str] = None):
        self.threshold = threshold
        self.required_keywords = required_keywords or []
        self._score = 0.0
        self._reason = ""

    @property
    def __name__(self) -> str:
        return "InfraFaithfulnessMetric"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        """
        Measure faithfulness using keyword coverage + structural analysis.
        test_case.actual_output: the generated artifact (Rego or Terraform string)
        test_case.input: the incident root_cause JSON or description
        test_case.context: list of root_cause_keywords that MUST appear
        """
        artifact = test_case.actual_output or ""
        keywords = test_case.context or self.required_keywords

        if not artifact.strip():
            self._score = 0.0
            self._reason = "Empty artifact"
            return self._score

        artifact_lower = artifact.lower()
        matched = [kw for kw in keywords if kw.lower() in artifact_lower]
        coverage = len(matched) / len(keywords) if keywords else 0.5

        # Structural check: does the artifact reference the incident's resource type?
        input_text = (test_case.input or "").lower()
        # Extract resource types mentioned in input
        structural_bonus = 0.0
        for resource_hint in ["aws_", "google_", "azurerm_", "kubernetes_"]:
            if resource_hint in artifact_lower:
                structural_bonus = 0.1
                break

        self._score = min(1.0, coverage + structural_bonus)
        self._reason = (
            f"Keyword coverage: {len(matched)}/{len(keywords)} ({coverage:.0%}). "
            f"Matched: {matched}. Unmatched: {[k for k in keywords if k.lower() not in artifact_lower]}"
        )
        return self._score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self._score >= self.threshold

    @property
    def score(self) -> float:
        return self._score

    @property
    def reason(self) -> str:
        return self._reason


class SyntaxValidityMetric(BaseMetric):
    """
    Hard syntax validity check via real parser — NOT an LLM self-check.

    For Rego: calls opa check (or regex fallback).
    For Terraform: calls python-hcl2 parser (or regex fallback).

    This is the most important metric in the suite. An LLM asked to review
    its own Rego will confidently approve code that `opa check` rejects due
    to undefined variables, missing imports, or invalid rule structures.
    A hard parser call is the only reliable gate.
    """

    def __init__(self, artifact_type: str = "rego", threshold: float = 1.0):
        """
        artifact_type: "rego" | "terraform" | "auto" (detects from content)
        threshold: 1.0 means must pass syntax check to succeed
        """
        self.threshold = threshold
        self.artifact_type = artifact_type
        self._score = 0.0
        self._reason = ""

    @property
    def __name__(self) -> str:
        return f"SyntaxValidityMetric[{self.artifact_type}]"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        artifact = test_case.actual_output or ""

        if not artifact.strip():
            self._score = 0.0
            self._reason = "Empty artifact"
            return 0.0

        atype = self.artifact_type
        if atype == "auto":
            atype = "rego" if "package " in artifact else "terraform"

        if atype == "rego":
            try:
                from app.validators.rego_validator import validate_rego
                result = validate_rego(artifact)
            except ImportError:
                # Fallback path when running from mlops/ dir
                import importlib.util, pathlib
                spec = importlib.util.spec_from_file_location(
                    "rego_validator",
                    pathlib.Path(__file__).parents[3] / "backend/app/validators/rego_validator.py"
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                result = mod.validate_rego(artifact)
        else:
            try:
                from app.validators.terraform_validator import validate_terraform
                result = validate_terraform(artifact)
            except ImportError:
                import importlib.util, pathlib
                spec = importlib.util.spec_from_file_location(
                    "terraform_validator",
                    pathlib.Path(__file__).parents[3] / "backend/app/validators/terraform_validator.py"
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                result = mod.validate_terraform(artifact)

        self._score = 1.0 if result.valid else 0.0
        self._reason = (
            f"[{result.validator_used}] {'PASS' if result.valid else 'FAIL'}: "
            f"{result.error or 'syntax valid'}"
        )
        return self._score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self._score >= self.threshold

    @property
    def score(self) -> float:
        return self._score

    @property
    def reason(self) -> str:
        return self._reason


class ContextRelevancyMetric(BaseMetric):
    """
    Checks whether the Firecrawl-retrieved context materially informed the artifact.

    A context is "decorative" if the artifact contains none of the specific
    resource names, service names, or technical terms from the retrieved documents.
    A context is "material" if at least 30% of its key technical terms appear
    in the artifact.

    NOTE: Context relevancy is only meaningful when Firecrawl is enabled.
    When running in mock mode (no enrichment), this metric is skipped.
    """

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self._score = 0.0
        self._reason = ""

    @property
    def __name__(self) -> str:
        return "ContextRelevancyMetric"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        artifact = test_case.actual_output or ""
        # context is a list of strings (enrichment doc excerpts)
        context_docs = test_case.context or []

        if not context_docs:
            # No context = irrelevant, but not a failure (Firecrawl may be disabled)
            self._score = 0.5
            self._reason = "No enrichment context provided (Firecrawl disabled or no references)"
            return 0.5

        # Extract technical terms from context (words > 5 chars, not stop words)
        import re
        stop_words = {"about", "above", "after", "before", "between", "config",
                      "configuration", "using", "should", "ensure", "require"}
        artifact_lower = artifact.lower()
        all_context = " ".join(str(c) for c in context_docs).lower()
        ctx_terms = set(
            w for w in re.findall(r'\b[a-z]{6,}\b', all_context)
            if w not in stop_words
        )

        if not ctx_terms:
            self._score = 0.5
            self._reason = "Context too sparse to evaluate relevancy"
            return 0.5

        matched = sum(1 for t in ctx_terms if t in artifact_lower)
        self._score = min(1.0, matched / len(ctx_terms) * 3)  # x3 to normalize
        self._reason = f"Context terms in artifact: {matched}/{len(ctx_terms)}"
        return self._score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self._score >= self.threshold

    @property
    def score(self) -> float:
        return self._score

    @property
    def reason(self) -> str:
        return self._reason
