"""CIRUS — Repository: Artifact."""
from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact, ArtifactType
from app.utils.ids import artifact_id
from app.utils.time import utcnow


class ArtifactRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upsert(
        self,
        incident_id: str,
        artifact_type: ArtifactType,
        content: dict,
        model_id: Optional[str] = None,
        tokens_used: Optional[int] = None,
    ) -> Artifact:
        """Create or replace an artifact for the given incident + type."""
        existing = await self.get_by_type(incident_id, artifact_type)
        if existing:
            existing.content = json.dumps(content)
            existing.version += 1
            existing.model_id = model_id
            existing.tokens_used = tokens_used
            existing.updated_at = utcnow()
            await self._db.flush()
            return existing

        artifact = Artifact(
            id=artifact_id(),
            incident_id=incident_id,
            artifact_type=artifact_type,
            content=json.dumps(content),
            version=1,
            model_id=model_id,
            tokens_used=tokens_used,
        )
        self._db.add(artifact)
        await self._db.flush()
        await self._db.refresh(artifact)
        return artifact

    async def get(self, id: str) -> Optional[Artifact]:
        result = await self._db.execute(select(Artifact).where(Artifact.id == id))
        return result.scalar_one_or_none()

    async def get_by_type(
        self, incident_id: str, artifact_type: ArtifactType
    ) -> Optional[Artifact]:
        result = await self._db.execute(
            select(Artifact).where(
                Artifact.incident_id == incident_id,
                Artifact.artifact_type == artifact_type,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_incident(self, incident_id: str) -> List[Artifact]:
        result = await self._db.execute(
            select(Artifact).where(Artifact.incident_id == incident_id)
        )
        return list(result.scalars().all())

    async def delete(self, id: str) -> bool:
        artifact = await self.get(id)
        if not artifact:
            return False
        await self._db.delete(artifact)
        await self._db.flush()
        return True
