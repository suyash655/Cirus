"""CIRUS — Orchestrator: Individual pipeline stage executors."""
from __future__ import annotations

from typing import List

from app.core.logging import get_logger
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
            id="normalization",
            label="Incident Normalization",
            description="Parse and extract structured data from raw incident text.",
        ),
        StageState(
            id="root-cause-classification",
            label="Root Cause Classification",
            description="Identify the root cause and contributing factors.",
        ),
        StageState(
            id="context-enrichment",
            label="Context Enrichment",
            description="Enrich with external runbooks and documentation.",
        ),
        StageState(
            id="artifact-generation",
            label="Artifact Generation",
            description=f"Generate: {', '.join(selected_artifacts)}.",
        ),
        StageState(
            id="validator-critic",
            label="Validator / Critic",
            description="Validate artifact quality and consistency.",
        ),
        StageState(
            id="risk-scoring",
            label="Risk Scoring",
            description="Compute before/after risk score.",
        ),
        StageState(
            id="citation-extraction",
            label="Citation Extraction",
            description="Extract evidence and citations from incident text.",
        ),
    ]


# ── Stage executors ───────────────────────────────────────────────────────────

async def run_normalization(state: PipelineState, llm: LLMService) -> None:
    stage = state.get_stage("normalization")
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
    stage = state.get_stage("root-cause-classification")
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
    stage = state.get_stage("context-enrichment")
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
    stage = state.get_stage("artifact-generation")
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
    stage = state.get_stage("validator-critic")
    stage.start()
    # Critic pass — validate artifact coherence (lightweight check)
    issues: list = []
    if not state.root_cause.get("root_cause"):
        issues.append("Root cause is empty.")
    if not state.artifacts_generated:
        issues.append("No artifacts were generated.")

    stage.complete(
        output={
            "passed": len(issues) == 0,
            "issues": issues,
        }
    )


async def run_risk_scoring(
    state: PipelineState, llm: LLMService, wolfram: WolframService
) -> None:
    stage = state.get_stage("risk-scoring")
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
    stage = state.get_stage("citation-extraction")
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
