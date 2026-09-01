"""CIRUS — Orchestrator: Main pipeline coordinator.

Runs all stages in order, updating the WorkflowRun record after each one.
Designed to be called from a background task (Celery or asyncio.create_task).
"""
from __future__ import annotations

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.run import WorkflowRunStatus
from app.orchestrator import stages as stage_runners
from app.orchestrator.state import PipelineState, StageState
from app.orchestrator.stages import _build_initial_stages
from app.repositories.citation_repository import CitationRepository
from app.schemas.citation import CitationCreate
from app.services.artifact_service import ArtifactService
from app.services.firecrawl_service import FirecrawlService
from app.services.incident_service import IncidentService
from app.services.llm_service import LLMService
from app.services.wolfram_service import WolframService
from app.services.workflow_service import WorkflowService

log = get_logger(__name__)


class CIRUSPipeline:
    """Orchestrates the full incident → artifact generation pipeline.

    Usage:
        pipeline = CIRUSPipeline(db)
        await pipeline.run(run_id, incident_id, raw_text, selected_artifacts)
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._llm = LLMService()
        self._firecrawl = FirecrawlService()
        self._wolfram = WolframService()
        self._workflow_svc = WorkflowService(db)
        self._incident_svc = IncidentService(db)
        self._artifact_svc = ArtifactService(db, self._llm)
        self._citation_repo = CitationRepository(db)

    async def run(
        self,
        run_id: str,
        incident_id: str,
        raw_text: str,
        selected_artifacts: List[str],
    ) -> PipelineState:
        """Execute the full pipeline. Returns final PipelineState."""

        state = PipelineState(
            run_id=run_id,
            incident_id=incident_id,
            raw_text=raw_text,
            selected_artifacts=selected_artifacts,
            stages=_build_initial_stages(selected_artifacts),
        )

        log.info("pipeline started", run_id=run_id, incident_id=incident_id)

        # Persist initial stage list
        await self._persist_stages(run_id, state)

        try:
            # ── Stage 1: Normalization ────────────────────────────────────────
            await self._run_stage(state, "normalization", run_id)
            await stage_runners.run_normalization(state, self._llm)
            await self._persist_stages(run_id, state)

            # ── Stage 2: Root Cause Classification ────────────────────────────
            await self._run_stage(state, "root-cause-classification", run_id)
            await stage_runners.run_root_cause(state, self._llm)
            await self._persist_stages(run_id, state)

            # ── Stage 3: Context Enrichment ───────────────────────────────────
            await self._run_stage(state, "context-enrichment", run_id)
            await stage_runners.run_context_enrichment(state, self._firecrawl)
            await self._persist_stages(run_id, state)

            # ── Stage 4: Artifact Generation ──────────────────────────────────
            await self._run_stage(state, "artifact-generation", run_id)
            await stage_runners.run_artifact_generation(
                state, self._llm, self._artifact_svc
            )
            await self._persist_stages(run_id, state)

            # ── Stage 5: Validator / Critic ───────────────────────────────────
            await self._run_stage(state, "validator-critic", run_id)
            await stage_runners.run_validator(state, self._llm)
            await self._persist_stages(run_id, state)

            # ── Stage 6: Risk Scoring ─────────────────────────────────────────
            await self._run_stage(state, "risk-scoring", run_id)
            await stage_runners.run_risk_scoring(state, self._llm, self._wolfram)
            await self._persist_stages(run_id, state)

            # ── Stage 7: Citation Extraction ──────────────────────────────────
            await self._run_stage(state, "citation-extraction", run_id)
            await stage_runners.run_citation_extraction(state, self._llm)
            await self._persist_stages(run_id, state)

            # ── Persist citations ─────────────────────────────────────────────
            if state.citations:
                citation_creates = [
                    CitationCreate(
                        text=c.get("text", ""),
                        source=c.get("source", "incident-text"),
                        relevance=float(c.get("relevance", 0.5)),
                        line_number=c.get("line_number"),
                    )
                    for c in state.citations
                    if c.get("text")
                ]
                await self._citation_repo.bulk_create(incident_id, citation_creates)

            # ── Mark incident ready ───────────────────────────────────────────
            await self._incident_svc.mark_ready(incident_id, state.artifacts_generated)

            # ── Mark run completed ────────────────────────────────────────────
            await self._workflow_svc.set_completed(run_id, state.total_tokens)
            log.info("pipeline completed", run_id=run_id, tokens=state.total_tokens)

        except Exception as e:
            log.error("pipeline failed", run_id=run_id, error=str(e))
            await self._incident_svc.mark_error(incident_id)
            await self._workflow_svc.set_failed(run_id, str(e))
            state.error = str(e)

        return state

    async def _run_stage(
        self, state: PipelineState, stage_id: str, run_id: str
    ) -> None:
        await self._workflow_svc.set_running(run_id, stage_id)

    async def _persist_stages(self, run_id: str, state: PipelineState) -> None:
        await self._workflow_svc.update_stages(run_id, state.all_stages_dict())
