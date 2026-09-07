"""CIRUS — Service: Incident business logic."""
from __future__ import annotations

import json
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.incident import Incident, IncidentStatus
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate, IncidentDetailRead, IncidentRead, IncidentUpdate

log = get_logger(__name__)


def _deserialize(incident: Incident) -> dict:
    """Convert JSON text fields back to Python lists."""

    def _val(v):
        """Extract .value from str-enum, otherwise return as-is."""
        return v.value if hasattr(v, "value") else v

    return {
        "id": incident.id,
        "title": incident.title,
        "summary": incident.summary,
        "severity": _val(incident.severity),
        "provider": _val(incident.provider),
        "status": _val(incident.status),
        "tags": json.loads(incident.tags or "[]"),
        "artifacts_ready": json.loads(incident.artifacts_ready or "[]"),
        "file_name": incident.file_name,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
        "raw_text": getattr(incident, "raw_text", ""),
        "detected_format": _val(getattr(incident, "detected_format", "plain")),
        "timeline": [],
    }


class IncidentService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = IncidentRepository(db)

    async def create_incident(
        self, payload: IncidentCreate
    ) -> Tuple[Incident, str]:
        """Create a new incident and return (incident, run_id placeholder)."""
        # Derive title from first non-empty line of raw text
        lines = [l.strip() for l in payload.raw_text.strip().splitlines() if l.strip()]
        title = lines[0].lstrip("#").strip()[:120] if lines else "Untitled Incident"
        summary = " ".join(lines[1:4])[:300] if len(lines) > 1 else "Processing…"

        incident = await self._repo.create(payload, title=title, summary=summary)
        log.info("incident created", id=incident.id, severity=incident.severity)
        return incident

    async def get_incident(self, id: str) -> IncidentDetailRead:
        incident = await self._repo.get(id)
        if not incident:
            raise NotFoundError("Incident", id)
        return IncidentDetailRead(**_deserialize(incident))

    async def list_incidents(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        provider: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[IncidentRead], int]:
        incidents, total = await self._repo.list_all(
            limit=limit,
            offset=offset,
            status=status,
            severity=severity,
            provider=provider,
            search=search,
        )
        return [IncidentRead(**_deserialize(i)) for i in incidents], total

    async def update_incident(self, id: str, patch: IncidentUpdate) -> IncidentRead:
        incident = await self._repo.update(id, patch)
        if not incident:
            raise NotFoundError("Incident", id)
        return IncidentRead(**_deserialize(incident))

    async def delete_incident(self, id: str) -> None:
        deleted = await self._repo.delete(id)
        if not deleted:
            raise NotFoundError("Incident", id)
        log.info("incident deleted", id=id)

    async def mark_ready(
        self, id: str, artifacts_ready: List[str]
    ) -> None:
        await self._repo.update_status(
            id, IncidentStatus.ready, artifacts_ready=artifacts_ready
        )

    async def mark_error(self, id: str) -> None:
        await self._repo.update_status(id, IncidentStatus.error)
