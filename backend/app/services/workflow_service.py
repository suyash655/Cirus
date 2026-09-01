"""CIRUS — Service: Workflow run management."""
from __future__ import annotations

import json
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.run import WorkflowRun, WorkflowRunStatus
from app.repositories.run_repository import RunRepository
from app.schemas.run import WorkflowRunRead, WorkflowStageRead

log = get_logger(__name__)


def _deserialize_run(run: WorkflowRun) -> WorkflowRunRead:
    stages_raw = json.loads(run.stages or "[]")
    stages = [WorkflowStageRead(**s) for s in stages_raw]
    return WorkflowRunRead(
        id=run.id,
        incident_id=run.incident_id,
        status=str(run.status.value) if hasattr(run.status, "value") else str(run.status),
        current_stage=run.current_stage,
        stages=stages,
        model_id=run.model_id,
        triggered_by=str(run.triggered_by),
        total_tokens_used=run.total_tokens_used,
        error_message=run.error_message,
        started_at=run.started_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
    )


class WorkflowService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = RunRepository(db)

    async def create_run(
        self,
        incident_id: str,
        model_id: str = "mock",
        triggered_by: str = "auto",
    ) -> WorkflowRunRead:
        run = await self._repo.create(incident_id, model_id=model_id, triggered_by=triggered_by)
        log.info("workflow run created", run_id=run.id, incident_id=incident_id)
        return _deserialize_run(run)

    async def get_run(self, run_id: str) -> WorkflowRunRead:
        run = await self._repo.get(run_id)
        if not run:
            raise NotFoundError("WorkflowRun", run_id)
        return _deserialize_run(run)

    async def get_run_by_incident(self, incident_id: str) -> Optional[WorkflowRunRead]:
        run = await self._repo.get_by_incident(incident_id)
        if not run:
            return None
        return _deserialize_run(run)

    async def update_stages(self, run_id: str, stages: List[dict]) -> None:
        await self._repo.update_stages(run_id, stages)

    async def set_running(self, run_id: str, current_stage: str) -> None:
        await self._repo.update_status(
            run_id, WorkflowRunStatus.running, current_stage=current_stage
        )

    async def set_completed(self, run_id: str, total_tokens: int) -> None:
        await self._repo.update_status(
            run_id, WorkflowRunStatus.completed, total_tokens=total_tokens
        )

    async def set_failed(self, run_id: str, error: str) -> None:
        await self._repo.update_status(
            run_id, WorkflowRunStatus.failed, error_message=error
        )
