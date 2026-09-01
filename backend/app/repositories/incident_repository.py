"""CIRUS — Repository: Incident."""
from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentStatus
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.utils.ids import incident_id
from app.utils.time import utcnow


class IncidentRepository:
    """Data-access layer for Incident. No business logic lives here."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, payload: IncidentCreate, title: str, summary: str) -> Incident:
        incident = Incident(
            id=incident_id(),
            title=title,
            summary=summary,
            raw_text=payload.raw_text,
            detected_format="plain",
            severity=payload.severity or "P3",
            provider=payload.provider or "Generic",
            status=IncidentStatus.processing,
            tags=json.dumps([]),
            artifacts_ready=json.dumps([]),
            file_name=payload.file_name,
        )
        self._db.add(incident)
        await self._db.flush()
        await self._db.refresh(incident)
        return incident

    async def get(self, id: str) -> Optional[Incident]:
        result = await self._db.execute(select(Incident).where(Incident.id == id))
        return result.scalar_one_or_none()

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> tuple[List[Incident], int]:
        q = select(Incident)
        if status:
            q = q.where(Incident.status == status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._db.execute(count_q)).scalar_one()
        q = q.order_by(Incident.created_at.desc()).limit(limit).offset(offset)
        result = await self._db.execute(q)
        return list(result.scalars().all()), total

    async def update_status(
        self,
        id: str,
        status: IncidentStatus,
        artifacts_ready: Optional[List[str]] = None,
    ) -> Optional[Incident]:
        incident = await self.get(id)
        if not incident:
            return None
        incident.status = status
        incident.updated_at = utcnow()
        if artifacts_ready is not None:
            incident.artifacts_ready = json.dumps(artifacts_ready)
        await self._db.flush()
        await self._db.refresh(incident)
        return incident

    async def update(self, id: str, patch: IncidentUpdate) -> Optional[Incident]:
        incident = await self.get(id)
        if not incident:
            return None
        data = patch.model_dump(exclude_none=True)
        if "tags" in data:
            data["tags"] = json.dumps(data["tags"])
        for field, value in data.items():
            setattr(incident, field, value)
        incident.updated_at = utcnow()
        await self._db.flush()
        await self._db.refresh(incident)
        return incident

    async def delete(self, id: str) -> bool:
        incident = await self.get(id)
        if not incident:
            return False
        await self._db.delete(incident)
        await self._db.flush()
        return True

    async def count_by_status(self) -> dict:
        result = await self._db.execute(
            select(Incident.status, func.count(Incident.id)).group_by(Incident.status)
        )
        return {row[0]: row[1] for row in result.all()}
