"""CIRUS — Repository: WorkflowRun."""
from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import WorkflowRun, WorkflowRunStatus
from app.utils.ids import run_id
from app.utils.time import utcnow


class RunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        incident_id: str,
        model_id: str = "mock",
        triggered_by: str = "auto",
    ) -> WorkflowRun:
        run = WorkflowRun(
            id=run_id(),
            incident_id=incident_id,
            status=WorkflowRunStatus.queued,
            stages=json.dumps([]),
            model_id=model_id,
            triggered_by=triggered_by,
        )
        self._db.add(run)
        await self._db.flush()
        await self._db.refresh(run)
        return run

    async def get(self, id: str) -> Optional[WorkflowRun]:
        result = await self._db.execute(select(WorkflowRun).where(WorkflowRun.id == id))
        return result.scalar_one_or_none()

    async def get_by_incident(self, incident_id: str) -> Optional[WorkflowRun]:
        result = await self._db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.incident_id == incident_id)
            .order_by(WorkflowRun.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_incident(self, incident_id: str) -> List[WorkflowRun]:
        result = await self._db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.incident_id == incident_id)
            .order_by(WorkflowRun.started_at.desc())
        )
        return list(result.scalars().all())

    async def update_stages(self, id: str, stages: list) -> Optional[WorkflowRun]:
        run = await self.get(id)
        if not run:
            return None
        run.stages = json.dumps(stages)
        run.updated_at = utcnow()
        await self._db.flush()
        return run

    async def update_status(
        self,
        id: str,
        status: WorkflowRunStatus,
        current_stage: Optional[str] = None,
        total_tokens: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Optional[WorkflowRun]:
        run = await self.get(id)
        if not run:
            return None
        run.status = status
        run.updated_at = utcnow()
        if current_stage is not None:
            run.current_stage = current_stage
        if total_tokens is not None:
            run.total_tokens_used = total_tokens
        if error_message is not None:
            run.error_message = error_message
        if status in (WorkflowRunStatus.completed, WorkflowRunStatus.failed):
            run.completed_at = utcnow()
        await self._db.flush()
        return run
