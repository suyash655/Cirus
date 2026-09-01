"""CIRUS — API endpoints: Knowledge base."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db
from app.models.knowledge import KnowledgeEntry
from app.utils.ids import knowledge_id
from app.utils.time import utcnow

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeEntryCreate(BaseModel):
    title: str
    content: str
    source_url: Optional[str] = None
    category: str = "general"
    cloud_provider: Optional[str] = None


class KnowledgeEntryRead(BaseModel):
    id: str
    title: str
    content: str
    source_url: Optional[str]
    category: str
    cloud_provider: Optional[str]
    relevance_score: float

    model_config = {"from_attributes": True}


@router.get(
    "/",
    response_model=List[KnowledgeEntryRead],
    summary="List knowledge entries",
    dependencies=[Depends(require_api_key)],
)
async def list_knowledge(
    category: Optional[str] = Query(default=None),
    cloud_provider: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(KnowledgeEntry)
    if category:
        q = q.where(KnowledgeEntry.category == category)
    if cloud_provider:
        q = q.where(KnowledgeEntry.cloud_provider == cloud_provider)
    q = q.order_by(KnowledgeEntry.relevance_score.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post(
    "/",
    response_model=KnowledgeEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a knowledge entry",
    dependencies=[Depends(require_api_key)],
)
async def create_knowledge_entry(
    payload: KnowledgeEntryCreate,
    db: AsyncSession = Depends(get_db),
):
    entry = KnowledgeEntry(
        id=knowledge_id(),
        **payload.model_dump(),
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge entry",
    dependencies=[Depends(require_api_key)],
)
async def delete_knowledge_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry:
        await db.delete(entry)
