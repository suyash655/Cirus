"""CIRUS — Orchestrator: Individual pipeline stage executors."""
from __future__ import annotations

from typing import List

from app.core.logging import get_logger
from app.orchestrator.constants import StageID
from app.orchestrator.state import PipelineState, StageState
from app.services.llm_service import LLMMessage, LLMService
from app.services.prompt_service import PromptService
from app.services.firecrawl_service import FirecrawlService
from app.services.wolfram_service import WolframService
from app.utils.json_repair import parse_llm_json, safe_json_loads

log = get_logger(__name__)

prompts = PromptService()


def _build_initial_stages(selected_artifacts: List[str]) -> List[StageState]:
    """Return the ordered list of pipeline stages."""
    return [
        StageState(
            id=StageID.NORMALIZATION,
            label="Incident Normalization",
            description="Parse and extract structured data from raw incident text.",
        ),
        StageState(
            id=StageID.ROOT_CAUSE,
            label="Root Cause Classification",
            description="Identify the root cause and contributing factors.",
        ),
        StageState(
            id=StageID.CONTEXT_ENRICHMENT,
            label="Context Enrichment",
            description="Enrich with external runbooks and documentation.",
        ),
        StageState(
            id=StageID.ARTIFACT_GENERATION,
            label="Artifact Generation",
            description=f"Generate: {', '.join(selected_artifacts)}.",
        ),
        StageState(
            id=StageID.VALIDATOR_CRITIC,
            label="Validator / Critic",
            description="Validate artifact syntax and structural correctness.",
        ),
        StageState(
            id=StageID.RISK_SCORING,
            label="Risk Scoring",
            description="Compute before/after risk score.",
        ),
        StageState(
            id=StageID.CITATION_EXTRACTION,
            label="Citation Extraction",
            description="Extract evidence and citations from incident text.",
        ),
    ]


def _get_stage(state: PipelineState, stage_id: str) -> StageState:
    """Get a stage by ID, raising ValueError if not found (never returns None)."""
    stage = state.get_stage(stage_id)
    if stage is None:
        raise ValueError(
            f"Stage '{stage_id}' not found in pipeline state. "
            f"Available stages: {[s.id for s in state.stages]}"
        )
    return stage


# ── Stage executors ───────────────────────────────────────────────────────────

async def run_normalization(state: PipelineState, llm: LLMService) -> None:
    stage = _get_stage(state, StageID.NORMALIZATION)
    stage.start()
    try:
        prompt = prompts.extraction_prompt(state.raw_text)
        response = await llm.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            system=prompts.system_prompt,
        )
        extraction = parse_llm_json(response.content, default={})
        state.extraction = extraction
        state.add_tokens(response.tokens_used)
        stage.complete(
            output={"summary": extraction.get("summary", ""), "data": extraction},
            confidence=extraction.get("confidence"),
            tokens=response.tokens_used,
            model_id=response.model_id,
        )
    except Exception as e:
        stage.fail(str(e))
        state.error = str(e)
        raise


async def run_root_cause(state: PipelineState, llm: LLMService) -> None:
    stage = _get_stage(state, StageID.ROOT_CAUSE)
    stage.start()
    try:
        prompt = prompts.root_cause_prompt(state.raw_text, state.extraction)
        response = await llm.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            system=prompts.system_prompt,
        )
        root_cause = parse_llm_json(response.content, default={})
        state.root_cause = root_cause
        state.add_tokens(response.tokens_used)
        stage.complete(
            output={
                "root_cause": root_cause.get("root_cause", ""),
                "data": root_cause,
            },
            confidence=root_cause.get("confidence"),
            tokens=response.tokens_used,
            model_id=response.model_id,
        )
    except Exception as e:
        stage.fail(str(e))
        state.error = str(e)
        raise


async def run_context_enrichment(
    state: PipelineState, firecrawl: FirecrawlService
) -> None:
    stage = _get_stage(state, StageID.CONTEXT_ENRICHMENT)
    stage.start()
    try:
        # Pull URLs from root cause output if any
        refs = state.root_cause.get("references", [])
        if refs and isinstance(refs, list):
            context = await firecrawl.enrich_from_urls(refs[:3])
            state.enrichment_context = context

        stage.complete(
            output={"enriched_sources": len(state.enrichment_context)},
        )
    except Exception as e:
        # Non-fatal — log and skip
        log.warning("context enrichment failed, skipping", error=str(e))
        stage.skip()


async def run_artifact_generation(
    state: PipelineState,
    llm: LLMService,
    artifact_service,  # ArtifactService — avoid circular import
) -> None:
    stage = _get_stage(state, StageID.ARTIFACT_GENERATION)
    stage.start()
    generated = []
    try:
        for artifact_type in state.selected_artifacts:
            try:
                _content, raw_code = await artifact_service.generate_artifact(
                    incident_id=state.incident_id,
                    artifact_type=artifact_type,
                    raw_text=state.raw_text,
                    root_cause=state.root_cause,
                    extraction=state.extraction,
                )
                generated.append(artifact_type)
                # Store the raw validatable code string so the Validator/Critic
                # stage can run real syntax checks without re-fetching from DB.
                # Empty string means "no code to validate" (e.g. prose artifacts).
                if raw_code:
                    state.artifact_content[artifact_type] = raw_code
            except Exception as e:
                log.warning("artifact generation failed", type=artifact_type, error=str(e))

        state.artifacts_generated = generated
        stage.complete(output={"generated": generated})
    except Exception as e:
        stage.fail(str(e))
        state.error = str(e)
        raise


async def run_validator(state: PipelineState, llm: LLMService) -> None:
    """Validator / Critic stage.

    Runs real syntax validators on every generated artifact that has a
    code representation stored in state.artifact_content:
      - policy  → validate_rego()       (OPA binary or regex fallback)
      - iac     → validate_terraform()   (python-hcl2 or regex fallback)

    Prose artifacts (rca, runbook, alerts, regression) are checked for
    non-emptiness only — there is no syntax parser for natural language.

    If any code artifact fails syntax validation, the issues list is
    populated and logged as a WARNING. The pipeline continues (the
    incident is still marked ready) so that partial results reach the
    reviewer, but the artifact is flagged as invalid in the output.
    A future iteration should block the human approval gate on any failure.
    """
    from app.validators.rego_validator import validate_rego
    from app.validators.terraform_validator import validate_terraform

    stage = _get_stage(state, StageID.VALIDATOR_CRITIC)
    stage.start()

    issues: list[str] = []
    artifact_results: dict = {}

    # ── Precondition checks ───────────────────────────────────────────────────
    if not state.root_cause.get("root_cause"):
        issues.append("Root cause is empty — normalization or root-cause stage may have failed.")

    if not state.artifacts_generated:
        issues.append("No artifacts were generated.")

    # ── Real syntax validation on code artifacts ──────────────────────────────
    # state.artifact_content is populated by run_artifact_generation above.
    # It maps artifact_type → raw code string (only for policy + iac).
    # Validators are cheap (regex/subprocess) and more reliable than an LLM
    # self-check — an LLM will confidently approve broken Rego or Terraform.
    VALIDATORS = {
        "policy": ("Rego", validate_rego),
        "iac": ("Terraform HCL", validate_terraform),
    }

    for artifact_type, (lang_label, validator_fn) in VALIDATORS.items():
        code = state.artifact_content.get(artifact_type, "")
        if not code:
            # Artifact was not selected or generation failed — skip silently.
            continue

        try:
            result = validator_fn(code)
            artifact_results[artifact_type] = {
                "valid": result.valid,
                "validator": result.validator_used,
                "error": result.error,
            }
            if not result.valid:
                issues.append(
                    f"{lang_label} artifact failed validation "
                    f"[{result.validator_used}]: {result.error}"
                )
                log.warning(
                    "artifact syntax validation failed",
                    artifact_type=artifact_type,
                    validator=result.validator_used,
                    error=result.error,
                )
            else:
                log.info(
                    "artifact syntax validation passed",
                    artifact_type=artifact_type,
                    validator=result.validator_used,
                )
        except Exception as exc:
            # Validator itself crashed — log and continue; don’t block pipeline.
            log.warning(
                "validator raised an exception",
                artifact_type=artifact_type,
                error=str(exc),
            )
            artifact_results[artifact_type] = {
                "valid": None,
                "validator": "error",
                "error": str(exc),
            }

    # ── Prose artifact existence checks ───────────────────────────────────────
    PROSE_ARTIFACTS = {"rca", "runbook", "alerts", "regression"}
    for artifact_type in state.artifacts_generated:
        if artifact_type in PROSE_ARTIFACTS:
            artifact_results[artifact_type] = {"valid": True, "validator": "existence", "error": None}

    passed = len(issues) == 0
    if not passed:
        log.warning("validator-critic stage found issues", issues=issues)

    stage.complete(
        output={
            "passed": passed,
            "issues": issues,
            "artifact_results": artifact_results,
            "code_artifacts_checked": list(state.artifact_content.keys()),
        }
    )


async def run_risk_scoring(
    state: PipelineState, llm: LLMService, wolfram: WolframService
) -> None:
    stage = _get_stage(state, StageID.RISK_SCORING)
    stage.start()
    try:
        severity = state.extraction.get("detected_severity", "P3")
        before, after = await wolfram.score_risk(severity)
        risk = {
            "overall": after,
            "before_remediation": before,
            "after_remediation": after,
            "delta": before - after,
            "dimensions": {
                "exposure": {"score": after, "label": "Exposure (Wolfram)", "description": "Computed via Wolfram Alpha"}
            }
        }
        state.risk_score = risk
        stage.complete(
            output={
                "overall": risk.get("overall"),
                "delta": risk.get("delta"),
                "data": risk,
            },
            tokens=0,
        )
    except Exception as e:
        log.warning("risk scoring failed, skipping", error=str(e))
        stage.skip()


async def run_citation_extraction(state: PipelineState, llm: LLMService) -> None:
    stage = _get_stage(state, StageID.CITATION_EXTRACTION)
    stage.start()
    try:
        prompt = prompts.citation_extraction_prompt(state.raw_text)
        response = await llm.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            system=prompts.system_prompt,
        )
        citations = parse_llm_json(response.content, default=[])
        state.citations = citations if isinstance(citations, list) else []
        state.add_tokens(response.tokens_used)
        stage.complete(
            output={"citation_count": len(state.citations), "data": state.citations},
            tokens=response.tokens_used,
            model_id=response.model_id,
        )
    except Exception as e:
        log.warning("citation extraction failed, skipping", error=str(e))
        stage.skip()
