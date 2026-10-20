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
from app.utils.pii_scrub import scrub_pii

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
        # Scrub PII before sending to any external AI service.
        # The original state.raw_text is preserved in the DB; only the
        # AI sees the redacted version.
        state.safe_text = scrub_pii(state.raw_text)
        prompt = prompts.extraction_prompt(state.safe_text)
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
        safe_text = state.safe_text or scrub_pii(state.raw_text)
        prompt = prompts.root_cause_prompt(safe_text, state.extraction)
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
        firecrawl_hits = 0
        similar_hits = 0

        # ── 1. Firecrawl: enrich from external URLs in root cause refs ────────
        refs = state.root_cause.get("references", [])
        if refs and isinstance(refs, list):
            context = await firecrawl.enrich_from_urls(refs[:3])
            state.enrichment_context = context
            firecrawl_hits = len(context)

        # ── 2. Vector store: find similar past incidents ───────────────────────
        try:
            from app.services.vector_store import query_similar
            similar = await query_similar(
                query_text=state.raw_text,
                exclude_id=state.incident_id,
            )
            if similar:
                # Inject similar incidents as enrichment context entries
                for hit in similar:
                    state.enrichment_context.append({
                        "source": "cirus-history",
                        "incident_id": hit["incident_id"],
                        "snippet": hit["raw_text_snippet"],
                        "similarity_pct": hit["similarity_pct"],
                        "metadata": hit.get("metadata", {}),
                    })
                similar_hits = len(similar)
                log.info(
                    "vector_store: injected similar incidents into context",
                    count=similar_hits,
                    incident_id=state.incident_id,
                )
        except Exception as vs_err:
            log.warning(f"vector_store: similarity search failed ({vs_err}), skipping")

        stage.complete(
            output={
                "enriched_sources": firecrawl_hits,
                "similar_incidents": similar_hits,
            },
        )
    except Exception as e:
        # Non-fatal — log and skip
        log.warning(f"context enrichment failed ({e}), skipping")
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
        safe_text = state.safe_text or scrub_pii(state.raw_text)
        for artifact_type in state.selected_artifacts:
            try:
                # generate_artifact now returns (content_dict, raw_code_str)
                _content, raw_code = await artifact_service.generate_artifact(
                    incident_id=state.incident_id,
                    artifact_type=artifact_type,
                    raw_text=safe_text,
                    root_cause=state.root_cause,
                    extraction=state.extraction,
                )
                generated.append(artifact_type)
                # Store raw code so the validator stage can inspect it without a DB round-trip.
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

    Validates generated code artifacts using real parsers:
      - Rego policy  : `opa check` binary (if installed) → regex fallback
      - Terraform IaC: `python-hcl2` parser → regex fallback

    Reads raw code strings from state.artifact_content, which is written by
    run_artifact_generation() in Stage 4.  Prose artifacts (rca, runbook,
    alerts, regression) are checked for existence only.
    """
    from app.validators.rego_validator import validate_rego
    from app.validators.terraform_validator import validate_terraform

    stage = _get_stage(state, StageID.VALIDATOR_CRITIC)
    stage.start()

    issues: list[str] = []
    artifact_results: dict = {}

    if not state.root_cause.get("root_cause"):
        issues.append("Root cause is empty — normalization may have failed.")

    if not state.artifacts_generated:
        issues.append("No artifacts were generated.")

    # ── Validate code artifacts (policy + iac) ────────────────────────────────
    VALIDATORS = {
        "policy": ("Rego", validate_rego),
        "iac": ("Terraform HCL", validate_terraform),
    }
    code_artifacts_checked: list[str] = []

    for artifact_type, (label, validator_fn) in VALIDATORS.items():
        raw_code = state.artifact_content.get(artifact_type, "")
        if not raw_code:
            # Not generated or content was empty — skip, do not fail
            continue
        result = validator_fn(raw_code)
        artifact_results[artifact_type] = {
            "valid": result.valid,
            "validator": result.validator_used,
            "error": result.error,
        }
        code_artifacts_checked.append(artifact_type)
        if result.valid:
            log.info(
                "artifact syntax valid",
                type=artifact_type,
                label=label,
                validator=result.validator_used,
            )
        else:
            issues.append(
                f"{label} ({artifact_type}) failed [{result.validator_used}]: {result.error}"
            )
            log.warning(
                "artifact syntax invalid",
                type=artifact_type,
                label=label,
                validator=result.validator_used,
                error=result.error,
            )

    # ── Check prose artifacts exist ───────────────────────────────────────────
    for artifact_type in ["rca", "runbook", "alerts", "regression"]:
        if artifact_type in state.artifacts_generated:
            # These are prose/JSON — no AST validator. Just confirm they were generated.
            artifact_results[artifact_type] = {"valid": True, "validator": "existence", "error": None}

    passed = len(issues) == 0
    if not passed:
        log.warning("validator-critic stage found issues", issues=issues)
    else:
        log.info("validator-critic stage passed", checked=code_artifacts_checked)

    stage.complete(
        output={
            "passed": passed,
            "issues": issues,
            "artifact_results": artifact_results,
            "code_artifacts_checked": code_artifacts_checked,
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
        safe_text = state.safe_text or scrub_pii(state.raw_text)
        prompt = prompts.citation_extraction_prompt(safe_text)
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
