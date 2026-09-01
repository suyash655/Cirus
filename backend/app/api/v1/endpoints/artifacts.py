"""CIRUS — API endpoints: Artifacts."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db
from app.schemas.artifact import ArtifactRead, ArtifactSetRead, RegenerateArtifactRequest
from app.services.artifact_service import ArtifactService
from app.services.incident_service import IncidentService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

_llm = LLMService()


def _svc(db: AsyncSession = Depends(get_db)) -> ArtifactService:
    return ArtifactService(db, _llm)


def _incident_svc(db: AsyncSession = Depends(get_db)) -> IncidentService:
    return IncidentService(db)


@router.get(
    "/{incident_id}",
    response_model=ArtifactSetRead,
    summary="Get all artifacts for an incident",
    dependencies=[Depends(require_api_key)],
)
async def get_artifact_set(
    incident_id: str, svc: ArtifactService = Depends(_svc)
):
    return await svc.get_artifact_set(incident_id)


@router.post(
    "/{incident_id}/regenerate",
    response_model=ArtifactRead,
    summary="Regenerate a single artifact",
    dependencies=[Depends(require_api_key)],
)
async def regenerate_artifact(
    incident_id: str,
    body: RegenerateArtifactRequest,
    svc: ArtifactService = Depends(_svc),
    incident_svc: IncidentService = Depends(_incident_svc),
):
    detail = await incident_svc.get_incident(incident_id)
    return await svc.regenerate(
        incident_id=incident_id,
        artifact_type=body.artifact_type,
        raw_text=detail.raw_text,
        root_cause={},
        extraction={},
    )
