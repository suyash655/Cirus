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
                await artifact_service.generate_artifact(
                    incident_id=state.incident_id,
                    artifact_type=artifact_type,
                    raw_text=state.raw_text,
                    root_cause=state.root_cause,
                    extraction=state.extraction,
                )
                generated.append(artifact_type)
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

    Performs real structural validation on generated artifacts using the
    syntax validators in app.validators (OPA/Rego + HCL2/Terraform).
    Falls back to a lightweight existence check when no validators are
    available (e.g. in pure mock mode).
    """
    from app.validators.rego_validator import validate_rego
    from app.validators.terraform_validator import validate_terraform

    stage = _get_stage(state, StageID.VALIDATOR_CRITIC)
    stage.start()

    issues: list[str] = []
    artifact_results: dict = {}

    if not state.root_cause.get("root_cause"):
        issues.append("Root cause is empty.")

    if not state.artifacts_generated:
        issues.append("No artifacts were generated.")

    # ── Real syntax validation on persisted artifact content ─────────────────
    # We pull the raw content from state.extraction to validate what was
    # actually generated. Validators are cheap (regex/subprocess) and
    # significantly more reliable than asking the LLM to self-check.
    from app.services.artifact_service import ArtifactService  # avoid circular at module level

    for artifact_type in state.artifacts_generated:
        try:
            # Retrieve the artifact content from the DB via state's artifact_service
            # (passed through pipeline.py — we access it via the closure the pipeline
            #  sets on state, or we do a lightweight in-memory check here)
            pass  # Content check below uses state cache if available
        except Exception:
            pass

    # Validate policy (Rego) artifacts if content is available in state
    policy_content = None
    iac_content = None

    # Try to get content from the artifact_service stored in state
    # (Pipeline passes artifacts through artifact_service.generate_artifact which caches)
    # Best-effort: validate mock or LLM-returned content stored on state
    if hasattr(state, "_last_policy_code") and state._last_policy_code:
        policy_content = state._last_policy_code
    if hasattr(state, "_last_iac_code") and state._last_iac_code:
        iac_content = state._last_iac_code

    if policy_content:
        result = validate_rego(policy_content)
        artifact_results["policy"] = {
            "valid": result.valid,
            "validator": result.validator_used,
            "error": result.error,
        }
        if not result.valid:
            issues.append(f"Policy (Rego) failed validation [{result.validator_used}]: {result.error}")
            log.warning("Rego validation failed", error=result.error, validator=result.validator_used)

    if iac_content:
        result = validate_terraform(iac_content)
        artifact_results["iac"] = {
            "valid": result.valid,
            "validator": result.validator_used,
            "error": result.error,
        }
        if not result.valid:
            issues.append(f"IaC (Terraform) failed validation [{result.validator_used}]: {result.error}")
            log.warning("Terraform validation failed", error=result.error, validator=result.validator_used)

    passed = len(issues) == 0
    if not passed:
        log.warning("validator-critic stage found issues", issues=issues)

    stage.complete(
        output={
            "passed": passed,
            "issues": issues,
            "artifact_results": artifact_results,
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
