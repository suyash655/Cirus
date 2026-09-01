"""CIRUS — Pydantic v2 schemas: WorkflowRun."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

WorkflowRunStatus = Literal["queued", "running", "completed", "failed"]
WorkflowStageStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class StageOutputRead(BaseModel):
    model_config = {"protected_namespaces": ()}

    summary: str
    data: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    tokens_used: Optional[int] = None
    model_id: Optional[str] = None


class WorkflowStageRead(BaseModel):
    id: str
    label: str
    description: str
    status: WorkflowStageStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    output: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    tokens_used: Optional[int] = None
    model_id: Optional[str] = None
    logs: Optional[List[str]] = None


class WorkflowRunRead(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: str
    incident_id: str
    status: WorkflowRunStatus
    current_stage: Optional[str] = None
    stages: List[WorkflowStageRead]
    model_id: str
    triggered_by: str
    total_tokens_used: Optional[int] = None
    error_message: Optional[str] = None
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class WorkflowRunListResponse(BaseModel):
    items: List[WorkflowRunRead]
    total: int
