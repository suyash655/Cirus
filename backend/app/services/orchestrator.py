"""CIRUS — Service: Main orchestrator for AI-powered incident workflow.

Coordinates the sequential execution of AI services for incident processing.
"""
import json
import logging
import uuid
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incident import Incident, IncidentStatus
from app.models.artifact import Artifact, ArtifactType
from app.models.citation import Citation, CitationSource
from app.services.llm_service import LLMProviderService
from app.services.firecrawl_service import get_context
from app.services.wolfram_service import calculate_risk

log = logging.getLogger(__name__)


async def run_workflow(incident_id: str, db: AsyncSession) -> None:
    """
    Execute the complete AI workflow for an incident.
    
    Sequential steps:
    1. Fetch incident from DB
    2. Normalize incident using Featherless AI
    3. Get context from Firecrawl
    4. Generate artifacts using Featherless AI
    5. Calculate risk scores using Wolfram
    6. Save artifacts and risk scores to DB
    7. Update incident status to completed
    
    If any step fails, update incident status to failed and save error message.
    
    Args:
        incident_id: The ID of the incident to process
        db: Async database session
    """
    # Initialize services
    llm_service = LLMProviderService()
    
    try:
        log.info("Starting workflow for incident", incident_id=incident_id)
        
        # Step 1: Fetch the Incident from the DB
        log.info("Step 1: Fetching incident from database", incident_id=incident_id)
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        
        if not incident:
            raise ValueError(f"Incident with ID {incident_id} not found")
        
        raw_text = incident.raw_text
        log.info("Incident fetched successfully", title=incident.title)
        
        # Step 2: Normalize incident using LLM service
        log.info("Step 2: Normalizing incident with LLM service")
        normalized_data = await llm_service.normalize_incident(raw_text)
        
        # Update incident with normalized data
        incident.title = normalized_data.get("title", incident.title)
        incident.summary = normalized_data.get("symptoms", incident.summary)
        # Note: provider and severity are enums, would need mapping logic
        log.info("Incident normalized successfully", normalized_title=incident.title)
        
        # Step 3: Get context from Firecrawl
        log.info("Step 3: Fetching context from Firecrawl")
        provider = normalized_data.get("provider", "Generic")
        root_cause = normalized_data.get("root_cause", "")
        context_citations = await get_context(provider, root_cause)
        
        # Save citations to database
        for citation_data in context_citations:
            citation = Citation(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                text=citation_data.get("snippet", ""),
                source=CitationSource.external,
                relevance=0.8,  # Default relevance
                url=citation_data.get("url", "")
            )
            db.add(citation)
        
        log.info("Context retrieved and citations saved", citation_count=len(context_citations))
        
        # Step 4: Generate artifacts using LLM service
        log.info("Step 4: Generating artifacts with LLM service")
        artifacts = await llm_service.generate_artifacts(normalized_data)
        
        # Save artifacts to database
        artifact_mappings = {
            "terraform": ArtifactType.iac,
            "policy": ArtifactType.policy,
            "runbook": ArtifactType.runbook
        }
        
        for artifact_key, artifact_type in artifact_mappings.items():
            content = artifacts.get(artifact_key, "")
            if content:
                artifact = Artifact(
                    id=str(uuid.uuid4()),
                    incident_id=incident_id,
                    artifact_type=artifact_type,
                    content=json.dumps({"content": content}),
                    version=1,
                    model_id=llm_service.model
                )
                db.add(artifact)
        
        log.info("Artifacts generated and saved", artifact_count=len(artifact_mappings))
        
        # Step 5: Calculate risk scores using Wolfram
        log.info("Step 5: Calculating risk scores")
        severity = normalized_data.get("severity", "medium")
        risk_before, risk_after = await calculate_risk(severity)
        
        # Save risk scores as a special artifact or update incident
        risk_artifact = Artifact(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            artifact_type=ArtifactType.rca,  # Using RCA type for risk analysis
            content=json.dumps({
                "risk_before": risk_before,
                "risk_after": risk_after,
                "severity": severity
            }),
            version=1,
            model_id="wolfram-fallback"
        )
        db.add(risk_artifact)
        
        log.info("Risk scores calculated and saved", risk_before=risk_before, risk_after=risk_after)
        
        # Step 6: Save all changes to database
        await db.commit()
        log.info("Database changes committed")
        
        # Step 7: Update incident status to completed (using 'ready' as equivalent)
        log.info("Step 7: Updating incident status to completed")
        incident.status = IncidentStatus.ready
        await db.commit()
        
        log.info("Workflow completed successfully", incident_id=incident_id)
        
    except Exception as e:
        log.error("Workflow failed", incident_id=incident_id, error=str(e))
        
        try:
            # Update incident status to failed (using 'error' as equivalent)
            result = await db.execute(select(Incident).where(Incident.id == incident_id))
            incident = result.scalar_one_or_none()
            
            if incident:
                incident.status = IncidentStatus.error
                
                # Save error message as a special artifact
                error_artifact = Artifact(
                    id=str(uuid.uuid4()),
                    incident_id=incident_id,
                    artifact_type=ArtifactType.rca,
                    content=json.dumps({
                        "error": str(e),
                        "error_type": type(e).__name__
                    }),
                    version=1,
                    model_id="system"
                )
                db.add(error_artifact)
                
                await db.commit()
                log.info("Incident status updated to failed with error message")
            
        except Exception as commit_error:
            log.error("Failed to update incident status after error", error=str(commit_error))
            await db.rollback()
        
        # Re-raise the exception for upstream handling
        raise
