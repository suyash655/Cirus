"""CIRUS — API endpoints: Exports."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db
from app.services.artifact_service import ArtifactService
from app.services.export_service import ExportService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/exports", tags=["exports"])

_llm = LLMService()
_export_svc = ExportService()


def _artifact_svc(db: AsyncSession = Depends(get_db)) -> ArtifactService:
    return ArtifactService(db, _llm)


@router.get(
    "/{incident_id}",
    summary="Export artifacts for an incident",
    dependencies=[Depends(require_api_key)],
)
async def export_incident(
    incident_id: str,
    format: Literal["json", "markdown", "zip"] = Query(default="json"),
    svc: ArtifactService = Depends(_artifact_svc),
):
    artifact_set = await svc.get_artifact_set(incident_id)
    artifact_dict = artifact_set.model_dump()

    if format == "json":
        data = _export_svc.export_as_json(incident_id, artifact_dict)
        return Response(
            content=data,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={incident_id}.json"},
        )
    elif format == "markdown":
        data = _export_svc.export_as_markdown(incident_id, artifact_dict)
        return Response(
            content=data,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={incident_id}.md"},
        )
    elif format == "zip":
        data = _export_svc.export_as_zip(incident_id, artifact_dict)
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={incident_id}.zip"},
        )
