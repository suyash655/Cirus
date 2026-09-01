"""CIRUS — Repository: Citation."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.citation import Citation, CitationSource
from app.schemas.citation import CitationCreate
from app.utils.ids import citation_id


class CitationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def bulk_create(
        self, incident_id: str, citations: List[CitationCreate]
    ) -> List[Citation]:
        objects = [
            Citation(
                id=citation_id(),
                incident_id=incident_id,
                text=c.text,
                source=c.source,
                relevance=c.relevance,
                line_number=c.line_number,
                url=c.url,
            )
            for c in citations
        ]
        self._db.add_all(objects)
        await self._db.flush()
        return objects

    async def list_by_incident(self, incident_id: str) -> List[Citation]:
        result = await self._db.execute(
            select(Citation)
            .where(Citation.incident_id == incident_id)
            .order_by(Citation.relevance.desc())
        )
        return list(result.scalars().all())

    async def get(self, id: str) -> Optional[Citation]:
        result = await self._db.execute(select(Citation).where(Citation.id == id))
        return result.scalar_one_or_none()

    async def delete_by_incident(self, incident_id: str) -> int:
        citations = await self.list_by_incident(incident_id)
        for c in citations:
            await self._db.delete(c)
        await self._db.flush()
        return len(citations)
