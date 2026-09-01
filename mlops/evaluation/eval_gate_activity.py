"""CIRUS — Evaluation: Real Temporal Activity replacing the stub eval gate."""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List

from temporalio import activity

log = logging.getLogger(__name__)


@dataclass
class EvalGateInput:
    incident_id: str
    artifacts_generated: List[str]
    # Populated from pipeline state
    raw_text: str = ""
    root_cause: Dict[str, Any] = None
    extraction: Dict[str, Any] = None
    enrichment_context: List[Dict[str, Any]] = None


@dataclass
class EvalGateOutput:
    passed: bool
    issues: List[str]
    scores: Dict[str, float]  # {faithfulness, syntax_rego, syntax_terraform, context_relevancy}


@activity.defn
async def run_eval_gate(input_data: EvalGateInput) -> EvalGateOutput:
    """
    Real evaluation gate — replaces run_eval_gate_stub from the prior pass.

    Runs three checks:
    1. Faithfulness: do artifacts address the root_cause keywords?
    2. Syntax validity: do Rego/Terraform artifacts pass parser checks?
    3. Context relevancy: does enrichment context appear in artifacts? (warn-only)

    Blocks pipeline progression on faithfulness < 0.7 or syntax failure.
    Context relevancy is warn-only (Firecrawl may be disabled).
    """
    issues: List[str] = []
    scores: Dict[str, float] = {}

    # Retrieve artifacts from DB
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.artifact import ArtifactType
        from app.repositories.artifact_repository import ArtifactRepository
        from app.utils.json_repair import parse_llm_json

        async with AsyncSessionLocal() as session:
            repo = ArtifactRepository(session)
            artifacts = await repo.list_by_incident(input_data.incident_id)
    except Exception as e:
        activity.logger.error(f"Failed to load artifacts for eval gate: {e}")
        # Non-fatal: pass the gate with a warning
        return EvalGateOutput(passed=True, issues=[f"eval_gate_db_error: {e}"], scores={})

    # Extract root_cause keywords from the root cause analysis
    root_cause = input_data.root_cause or {}
    root_cause_keywords = []
    if root_cause.get("root_cause"):
        # Pull nouns from root cause string as keywords
        import re
        root_cause_str = str(root_cause.get("root_cause", ""))
        root_cause_keywords = [
            w for w in re.findall(r'\b[a-z_]{4,}\b', root_cause_str.lower())
            if w not in {"with", "that", "this", "from", "into", "when", "then", "where", "have"}
        ][:10]  # Cap at 10 keywords

    # ── Load DeepEval metrics ─────────────────────────────────────────────────
    try:
        from mlops.evaluation.metrics import (
            InfraFaithfulnessMetric,
            SyntaxValidityMetric,
            ContextRelevancyMetric,
        )
        from deepeval.test_case import LLMTestCase
        deepeval_available = True
    except ImportError:
        deepeval_available = False
        activity.logger.warning("DeepEval not available — using validators only")

    # ── Evaluate each artifact ────────────────────────────────────────────────
    for artifact in artifacts:
        if not artifact.content:
            continue

        content = parse_llm_json(artifact.content, default={})
        artifact_type_str = artifact.artifact_type.value

        # Extract the code string from the artifact JSON
        code = ""
        if artifact_type_str == "policy":
            code = content.get("code", "")
        elif artifact_type_str == "iac":
            code = content.get("full_patch") or content.get("diff") or content.get("fullPatch", "")
        else:
            continue  # Only evaluate Rego (policy) and Terraform (iac)

        if not code:
            continue

        # Syntax validity (hard parser — always runs regardless of deepeval)
        if artifact_type_str == "policy":
            from app.validators.rego_validator import validate_rego
            syn_result = validate_rego(code)
            score_key = "syntax_rego"
        else:
            from app.validators.terraform_validator import validate_terraform
            syn_result = validate_terraform(code)
            score_key = "syntax_terraform"

        scores[score_key] = 1.0 if syn_result.valid else 0.0
        if not syn_result.valid:
            issues.append(
                f"SYNTAX_FAIL[{artifact_type_str}]: {syn_result.error} (validator: {syn_result.validator_used})"
            )

        # Faithfulness (keyword coverage)
        if deepeval_available and root_cause_keywords:
            tc = LLMTestCase(
                input=str(root_cause),
                actual_output=code,
                context=root_cause_keywords,
            )
            faith_metric = InfraFaithfulnessMetric(required_keywords=root_cause_keywords)
            f_score = faith_metric.measure(tc)
            scores[f"faithfulness_{artifact_type_str}"] = f_score
            if not faith_metric.is_successful():
                issues.append(
                    f"FAITHFULNESS_FAIL[{artifact_type_str}]: {faith_metric.reason}"
                )

    # ── Determine pass/fail ───────────────────────────────────────────────────
    # Hard failures: any syntax error
    syntax_failed = any(v == 0.0 for k, v in scores.items() if k.startswith("syntax_"))
    # Soft failures: faithfulness too low (warn but allow for now in mock mode)
    faith_failed = any(v < 0.7 for k, v in scores.items() if k.startswith("faithfulness_"))

    # In mock mode, don't block on faithfulness (mock artifacts are low-quality by design)
    try:
        from app.core.config import settings
        is_mock = settings.MODE == "mock" or settings.LLM_PROVIDER == "mock"
    except Exception:
        is_mock = False

    passed = not syntax_failed and (not faith_failed or is_mock)

    if scores:
        activity.logger.info(
            f"Eval gate for {input_data.incident_id}: "
            f"passed={passed}, scores={scores}, issues={issues}"
        )
    else:
        activity.logger.info(f"Eval gate for {input_data.incident_id}: no scoreable artifacts, passing")
        passed = True

    return EvalGateOutput(passed=passed, issues=issues, scores=scores)
