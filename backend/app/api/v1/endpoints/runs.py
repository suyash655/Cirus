"""CIRUS — API endpoints: Workflow Runs."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db
from app.schemas.run import WorkflowRunRead
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/runs", tags=["runs"])


def _svc(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)


@router.get(
    "/{run_id}",
    response_model=WorkflowRunRead,
    summary="Get a workflow run by ID",
    dependencies=[Depends(require_api_key)],
)
async def get_run(run_id: str, svc: WorkflowService = Depends(_svc)):
    return await svc.get_run(run_id)


@router.get(
    "/by-incident/{incident_id}",
    response_model=WorkflowRunRead | None,
    summary="Get the latest workflow run for an incident",
    dependencies=[Depends(require_api_key)],
)
async def get_run_by_incident(
    incident_id: str, svc: WorkflowService = Depends(_svc)
):
    return await svc.get_run_by_incident(incident_id)
