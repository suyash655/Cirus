"""CIRUS — Orchestrator: Temporal Activities."""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from temporalio import activity

from app.db.session import AsyncSessionLocal
from app.services.llm_service import LLMMessage, LLMService
from app.services.prompt_service import PromptService
from app.services.firecrawl_service import FirecrawlService
from app.services.wolfram_service import WolframService
from app.services.artifact_service import ArtifactService
from app.utils.json_repair import parse_llm_json

prompts = PromptService()

@dataclass
class NormalizationInput:
    raw_text: str

@dataclass
class NormalizationOutput:
    extraction: Dict[str, Any]
    tokens_used: int
    confidence: Optional[float]
    model_id: Optional[str]

@activity.defn
async def normalize_incident(input_data: NormalizationInput) -> NormalizationOutput:
    llm = LLMService()
    prompt = prompts.extraction_prompt(input_data.raw_text)
    response = await llm.complete(
        messages=[LLMMessage(role="user", content=prompt)],
        system=prompts.system_prompt,
    )
    extraction = parse_llm_json(response.content, default={})
    return NormalizationOutput(
        extraction=extraction,
        tokens_used=response.tokens_used,
        confidence=extraction.get("confidence"),
        model_id=response.model_id
    )


@dataclass
class RootCauseInput:
    raw_text: str
    extraction: Dict[str, Any]

@dataclass
class RootCauseOutput:
    root_cause: Dict[str, Any]
    tokens_used: int
    confidence: Optional[float]
    model_id: Optional[str]

@activity.defn
async def classify_root_cause(input_data: RootCauseInput) -> RootCauseOutput:
    llm = LLMService()
    prompt = prompts.root_cause_prompt(input_data.raw_text, input_data.extraction)
    response = await llm.complete(
        messages=[LLMMessage(role="user", content=prompt)],
        system=prompts.system_prompt,
    )
    root_cause = parse_llm_json(response.content, default={})
    return RootCauseOutput(
        root_cause=root_cause,
        tokens_used=response.tokens_used,
        confidence=root_cause.get("confidence"),
        model_id=response.model_id
    )


@dataclass
class ContextEnrichmentInput:
    root_cause: Dict[str, Any]

@dataclass
class ContextEnrichmentOutput:
    enrichment_context: List[Dict[str, Any]]

@activity.defn
async def enrich_context(input_data: ContextEnrichmentInput) -> ContextEnrichmentOutput:
    firecrawl = FirecrawlService()
    refs = input_data.root_cause.get("references", [])
    if refs and isinstance(refs, list):
        context = await firecrawl.enrich_from_urls(refs[:3])
        return ContextEnrichmentOutput(enrichment_context=context)
    return ContextEnrichmentOutput(enrichment_context=[])


@dataclass
class ArtifactGenerationInput:
    incident_id: str
    raw_text: str
    selected_artifacts: List[str]
    root_cause: Dict[str, Any]
    extraction: Dict[str, Any]

@dataclass
class ArtifactGenerationOutput:
    generated: List[str]

@activity.defn
async def generate_artifacts(input_data: ArtifactGenerationInput) -> ArtifactGenerationOutput:
    llm = LLMService()
    generated = []
    # We need a DB session for ArtifactService
    async with AsyncSessionLocal() as session:
        artifact_service = ArtifactService(session, llm)
        for artifact_type in input_data.selected_artifacts:
            try:
                await artifact_service.generate_artifact(
                    incident_id=input_data.incident_id,
                    artifact_type=artifact_type,
                    raw_text=input_data.raw_text,
                    root_cause=input_data.root_cause,
                    extraction=input_data.extraction,
                )
                generated.append(artifact_type)
            except Exception as e:
                activity.logger.warning(f"artifact generation failed for {artifact_type}: {e}")
        
        await session.commit()
        
    return ArtifactGenerationOutput(generated=generated)


@dataclass
class EvalGateInput:
    incident_id: str
    artifacts_generated: List[str]

@dataclass
class EvalGateOutput:
    passed: bool
    issues: List[str]

@activity.defn
async def run_eval_gate_stub(input_data: EvalGateInput) -> EvalGateOutput:
    """
    # TODO(opus-phase1): replace with real eval gate (DeepEval/Ragas + AST validation).
    Currently this is a stub that always passes so the pipeline can continue.
    """
    activity.logger.info("Running eval gate stub...")
    return EvalGateOutput(passed=True, issues=[])


@dataclass
class RiskScoringInput:
    root_cause: Dict[str, Any]
    extraction: Dict[str, Any]
    artifacts_generated: List[str]

@dataclass
class RiskScoringOutput:
    risk_score: Dict[str, Any]
    tokens_used: int

@activity.defn
async def score_risk(input_data: RiskScoringInput) -> RiskScoringOutput:
    from app.services.wolfram_service import WolframService
    wolfram = WolframService()
    severity = input_data.extraction.get("detected_severity", "P3") if input_data.extraction else "P3"
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
    return RiskScoringOutput(risk_score=risk, tokens_used=0)


@dataclass
class CitationExtractionInput:
    raw_text: str

@dataclass
class CitationExtractionOutput:
    citations: List[Dict[str, Any]]
    tokens_used: int
    model_id: Optional[str]

@activity.defn
async def extract_citations(input_data: CitationExtractionInput) -> CitationExtractionOutput:
    llm = LLMService()
    prompt = prompts.citation_extraction_prompt(input_data.raw_text)
    response = await llm.complete(
        messages=[LLMMessage(role="user", content=prompt)],
        system=prompts.system_prompt,
    )
    citations = parse_llm_json(response.content, default=[])
    if not isinstance(citations, list):
        citations = []
    return CitationExtractionOutput(citations=citations, tokens_used=response.tokens_used, model_id=response.model_id)

@dataclass
class UpdateIncidentStatusInput:
    incident_id: str
    status: str

@activity.defn
async def update_incident_status(input_data: UpdateIncidentStatusInput) -> None:
    from app.models.incident import Incident
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Incident).where(Incident.id == input_data.incident_id))
        incident = result.scalar_one_or_none()
        if incident:
            incident.status = input_data.status
            await session.commit()

@dataclass
class UpdateRunStatusInput:
    run_id: str
    status: str
    current_stage: Optional[str] = None
    total_tokens: Optional[int] = None
    error: Optional[str] = None

@activity.defn
async def update_run_status(input_data: UpdateRunStatusInput) -> None:
    from app.services.workflow_service import WorkflowService
    async with AsyncSessionLocal() as session:
        svc = WorkflowService(session)
        if input_data.status == "running":
            await svc.set_running(input_data.run_id, input_data.current_stage or "unknown")
        elif input_data.status == "completed":
            await svc.set_completed(input_data.run_id, input_data.total_tokens or 0)
        elif input_data.status == "failed":
            await svc.set_failed(input_data.run_id, input_data.error or "Unknown error")
        await session.commit()
