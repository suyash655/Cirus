"""CIRUS — API endpoints: Incidents."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db, AsyncSessionLocal
from app.schemas.incident import (
    IncidentCreate,
    IncidentCreateResponse,
    IncidentDetailRead,
    IncidentListResponse,
    IncidentRead,
    IncidentUpdate,
)
from app.services.incident_service import IncidentService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/incidents", tags=["incidents"])

log = get_logger(__name__)


def _incident_svc(db: AsyncSession = Depends(get_db)) -> IncidentService:
    return IncidentService(db)


def _workflow_svc(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)


async def _run_pipeline_bg(
    run_id: str,
    incident_id: str,
    raw_text: str,
    selected_artifacts: list,
) -> None:
    """Background pipeline runner.

    Opens its own DB session so it is fully decoupled from the request
    session. Uses FastAPI BackgroundTasks (not asyncio.create_task) so
    the ASGI server waits for this coroutine to finish before recycling
    the connection. Incidents stuck in 'processing' on shutdown will be
    retried by Temporal when it is enabled.
    """
    from app.orchestrator.pipeline import CIRUSPipeline

    async with AsyncSessionLocal() as _db:
        try:
            pipeline = CIRUSPipeline(_db)
            await pipeline.run(run_id, incident_id, raw_text, selected_artifacts)
            await _db.commit()
        except Exception as exc:
            await _db.rollback()
            log.error("background pipeline error", run_id=run_id, error=str(exc))


@router.post(
    "/",
    response_model=IncidentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new incident for processing",
    dependencies=[Depends(require_api_key)],
)
async def create_incident(
    payload: IncidentCreate,
    background_tasks: BackgroundTasks,
    svc: IncidentService = Depends(_incident_svc),
    workflow_svc: WorkflowService = Depends(_workflow_svc),
):
    incident = await svc.create_incident(payload)
    run = await workflow_svc.create_run(
        incident_id=incident.id,
        model_id=(settings.FEATHERLESS_MODEL if settings.LLM_PROVIDER == "featherless"
                  else settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq"
                  else settings.OPENAI_MODEL if settings.LLM_PROVIDER == "openai"
                  else settings.LLM_PROVIDER),
        triggered_by="auto",
    )

    # Try Temporal first (if enabled); fall back to BackgroundTasks if unavailable
    temporal_ok = False
    if settings.TEMPORAL_ENABLED:
        try:
            from app.orchestrator.temporal_client import get_temporal_client
            from app.orchestrator.temporal_workflows import CIRUSWorkflow

            client = await get_temporal_client()
            await client.start_workflow(
                CIRUSWorkflow.run,
                args=[
                    run.id,
                    incident.id,
                    payload.raw_text,
                    payload.selected_artifacts,
                ],
                id=f"cirus-pipeline-{incident.id}-{run.id}",
                task_queue=settings.TEMPORAL_TASK_QUEUE,
            )
            temporal_ok = True
            log.info("temporal workflow started", run_id=run.id, incident_id=incident.id)
        except Exception as e:
            log.warning("temporal unavailable, falling back to BackgroundTasks", error=str(e))
    else:
        log.debug("temporal disabled (TEMPORAL_ENABLED=false), using BackgroundTasks")

    if not temporal_ok:
        # Use FastAPI BackgroundTasks — the ASGI server tracks these properly,
        # unlike bare asyncio.create_task() which is silently dropped on shutdown.
        background_tasks.add_task(
            _run_pipeline_bg,
            run.id,
            incident.id,
            payload.raw_text,
            payload.selected_artifacts or [],
        )

    return IncidentCreateResponse(id=incident.id, estimated_processing_ms=8000)


@router.get(
    "/",
    response_model=IncidentListResponse,
    summary="List all incidents with optional filtering and search",
    dependencies=[Depends(require_api_key)],
)
async def list_incidents(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (e.g. P1, P2, P3, P4)"),
    provider: Optional[str] = Query(default=None, description="Filter by cloud provider (e.g. AWS, GCP, Azure, Kubernetes)"),
    search: Optional[str] = Query(default=None, description="Search keyword in title, summary, or ID"),
    svc: IncidentService = Depends(_incident_svc),
):
    items, total = await svc.list_incidents(
        limit=limit,
        offset=offset,
        status=status_filter,
        severity=severity,
        provider=provider,
        search=search,
    )
    return IncidentListResponse(items=items, total=total)


@router.get(
    "/{incident_id}",
    response_model=IncidentDetailRead,
    summary="Get incident detail",
    dependencies=[Depends(require_api_key)],
)
async def get_incident(
    incident_id: str,
    svc: IncidentService = Depends(_incident_svc),
):
    return await svc.get_incident(incident_id)


@router.patch(
    "/{incident_id}",
    response_model=IncidentRead,
    summary="Update incident fields",
    dependencies=[Depends(require_api_key)],
)
async def update_incident(
    incident_id: str,
    patch: IncidentUpdate,
    svc: IncidentService = Depends(_incident_svc),
):
    return await svc.update_incident(incident_id, patch)


@router.delete(
    "/{incident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an incident",
    dependencies=[Depends(require_api_key)],
)
async def delete_incident(
    incident_id: str,
    svc: IncidentService = Depends(_incident_svc),
):
    await svc.delete_incident(incident_id)
    # Remove from vector store (non-fatal if it fails)
    try:
        from app.services.vector_store import delete_incident as vs_delete
        await vs_delete(incident_id)
    except Exception as e:
        log.warning("vector_store: delete failed (non-fatal)", error=str(e))


@router.get(
    "/{incident_id}/similar",
    summary="Find semantically similar past incidents",
    dependencies=[Depends(require_api_key)],
)
async def get_similar_incidents(
    incident_id: str,
    top_k: int = Query(default=5, le=20, description="Number of similar incidents to return"),
    svc: IncidentService = Depends(_incident_svc),
):
    """Return the top-k most semantically similar incidents from the vector store.

    Uses the incident's raw_text as the query embedding. Excludes the incident
    itself from results. Returns an empty list if the vector store is disabled
    or has no data yet.
    """
    incident = await svc.get_incident(incident_id)
    raw_text = incident.raw_text if hasattr(incident, "raw_text") else ""

    try:
        from app.services.vector_store import query_similar
        similar = await query_similar(
            query_text=raw_text,
            top_k=top_k,
            exclude_id=incident_id,
        )
    except Exception as e:
        log.warning("vector_store: similarity query failed", error=str(e))
        similar = []

    return {
        "incident_id": incident_id,
        "total": len(similar),
        "similar": similar,
    }
